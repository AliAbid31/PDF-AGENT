import io
import re
import time
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.agent.graph import agent
from app.api import auth
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import Base, engine, get_db, SessionLocal
from app.models.document import DocumentChunk
from app.models.user import User
from app.services.azure_storage import azure_storage
from app.services.email_service import send_email
from app.services.pdf_engine import (
    clean_extracted_text,
    generate_pdf,
    review_summary_text,
    validate_pdf_bytes,
)

Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    connection.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR"
    ))
    connection.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE"
    ))
    connection.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_code VARCHAR(6)"
    ))
    connection.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_password_code VARCHAR(6)"
    ))
    connection.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP"
    ))
    connection.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)"
    ))
    connection.execute(text(
        """
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            key VARCHAR(512) PRIMARY KEY,
            window_started TIMESTAMP NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0
        )
        """
    ))

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ali-pdf-agent.live",  # Ton domaine personnalisé
        "https://ali-pdf-agent.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")


def _generated_document_from_description(description: str) -> tuple[str, str]:
    prompt = f"""
Create a complete, original professional document based only on this user
request:

{description}

Return exactly this format:
DOCUMENT_TITLE: a concise, specific title that reflects the requested subject
DOCUMENT_CONTENT:
the complete document

Write the document itself, not a plan or an explanation of what you would do.
Use a clear title, logical section headings, concise paragraphs, lists where
useful, and a conclusion when appropriate. Keep the requested language,
audience, scope, and approximate length. Do not mention PDFs, AI, prompts,
uploaded files, or missing source documents.
"""
    content = None
    last_error = None
    for model_name in ("gemini-3.8-flash", "gemini-3.5-flash"):
        for attempt in range(2):
            try:
                model = ChatGoogleGenerativeAI(
                    model=model_name,
                    streaming=False,
                    api_key=settings.GEMINI_API_KEY,
                )
                content = model.invoke(prompt).content
                break
            except Exception as error:
                last_error = error
                error_text = str(error).casefold()
                temporary = any(
                    marker in error_text
                    for marker in (
                        "404",
                        "not_found",
                        "not found",
                        "503",
                        "429",
                        "unavailable",
                        "resource exhausted",
                    )
                )
                if not temporary:
                    raise
                if attempt == 0:
                    time.sleep(1)
        if content is not None:
            break
    if content is None:
        raise RuntimeError(
            "The text-generation service is temporarily unavailable. "
            "Please try again in a moment."
        ) from last_error

    if isinstance(content, list):
        content = "\n".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    generated = str(content).strip()
    if not generated:
        raise RuntimeError("The model returned empty content for the requested PDF.")

    title_match = re.search(
        r"(?im)^[ \t]*DOCUMENT_TITLE[ \t]*:[ \t]*(.+?)[ \t]*$", generated
    )
    content_match = re.search(
        r"(?ism)^[ \t]*DOCUMENT_CONTENT[ \t]*:[ \t]*(.+)$", generated
    )
    if title_match and content_match:
        title = title_match.group(1).strip()
        document_content = content_match.group(1).strip()
    else:
        lines = [line.strip() for line in generated.splitlines() if line.strip()]
        title = lines[0].lstrip("#").strip() if lines else "Generated Document"
        document_content = generated

    title = re.sub(r"\s+", " ", title).strip(" -*:_")
    if not title:
        title = "Generated Document"
    if not document_content:
        raise RuntimeError("The model returned empty content for the requested PDF.")
    return title[:160], document_content


def _safe_filename(value: str) -> str:
    filename = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    filename = re.sub(r"[\s-]+", "_", filename).strip("_")
    return (filename or "Generated_Document")[:120] + ".pdf"


def _is_description_document_request(question: str) -> bool:
    normalized = question.casefold()
    return (
        any(
            verb in normalized
            for verb in ("generate", "create", "rédige", "rédiger", "crée", "écris")
        )
        and any(
            noun in normalized
            for noun in (
                "document",
                "report",
                "rapport",
                "étude",
                "study",
                "essay",
                "article",
                "guide",
            )
        )
        and not any(
            phrase in normalized
            for phrase in ("summary of", "résumé de", "summarize", "résumer")
        )
    )


def _summary_title(document_name: str | None) -> str:
    if not document_name:
        return "Document Summary"
    source_name = re.sub(r"(?i)\.pdf$", "", document_name)
    source_name = re.sub(r"[_-]+", " ", source_name).strip()
    return f"Summary - {source_name}" if source_name else "Document Summary"


@app.get("/api/documents")
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            """
            SELECT document_name, COUNT(DISTINCT page_number) AS page_count,
                   COUNT(*) AS chunk_count
            FROM document_chunks
            WHERE user_id = :uid
            GROUP BY document_name
            ORDER BY document_name
            """
        ),
        {"uid": str(current_user.id)},
    ).mappings().all()
    return [
        {
            "name": row["document_name"],
            "pages": row["page_count"],
            "chunks": row["chunk_count"],
        }
        for row in rows
    ]


@app.post("/api/documents/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are allowed."
        )

    file_bytes = await file.read()

    azure_url = azure_storage.upload_file(file_bytes, file.filename)

    reader = PdfReader(io.BytesIO(file_bytes))
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview", google_api_key=settings.GEMINI_API_KEY
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150
    )

    chunks_to_create = []
    for page_idx, page in enumerate(reader.pages):
        extracted = ""
        try:
            extracted = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            extracted = page.extract_text() or ""
        if len(extracted.strip()) < 20:
            extracted = page.extract_text() or extracted
        text_content = clean_extracted_text(extracted)
        if not text_content:
            continue

        page_chunks = text_splitter.split_text(text_content)
        for chunk in page_chunks:
            vec = embeddings.embed_query(chunk)
            chunks_to_create.append(
                DocumentChunk(
                    user_id=current_user.id,
                    document_name=file.filename,
                    page_number=page_idx + 1,
                    content=chunk,
                    embedding=vec,
                )
            )

    if not chunks_to_create:
        raise HTTPException(
            status_code=422,
            detail=(
                "No selectable text was found in this PDF. It may be scanned "
                "or image-only; upload a text-readable PDF or run OCR first."
            ),
        )

    db.query(DocumentChunk).filter(
        DocumentChunk.user_id == current_user.id,
        DocumentChunk.document_name == file.filename,
    ).delete(synchronize_session=False)
    db.bulk_save_objects(chunks_to_create)
    db.commit()

    return {
        "message": "Document Vectorised and stored successfully",
        "url": azure_url,
        "chunks": len(chunks_to_create),
    }


@app.post("/api/chat")
async def chat_with_agent(
    question: str, current_user: User = Depends(get_current_user)
):
    normalized_question = question.casefold()
    is_pdf_resume_request = (
        "resume" in normalized_question
        or "résumé" in normalized_question
        or "pdf" in normalized_question
        or (
            any(
                verb in normalized_question
                for verb in ("generate", "create", "rédige", "rédiger", "crée")
            )
            and any(
                noun in normalized_question
                for noun in ("document", "report", "rapport", "étude", "study")
            )
        )
    )

    if is_pdf_resume_request:
        try:
            title = "Document Summary"
            db = SessionLocal()
            try:
                rows = db.execute(
                    text(
                        """
                        SELECT document_name, page_number, content
                        FROM document_chunks
                        WHERE user_id = :uid
                        ORDER BY document_name, page_number, id
                        """
                    ),
                    {"uid": str(current_user.id)},
                ).fetchall()
            finally:
                db.close()

            if _is_description_document_request(question):
                title, passages = _generated_document_from_description(question)
            elif rows:
                pages: list[str] = []
                current_page: tuple[str, int] | None = None
                page_content: list[str] = []
                for row in rows:
                    page_key = (row.document_name, row.page_number)
                    if current_page is not None and page_key != current_page:
                        pages.append(
                            f"Page {current_page[1]} - {current_page[0]}\n"
                            + "\n".join(page_content)
                        )
                        page_content = []
                    current_page = page_key
                    cleaned = review_summary_text(row.content)
                    if cleaned:
                        page_content.append(cleaned)
                if current_page is not None:
                    pages.append(
                        f"Page {current_page[1]} - {current_page[0]}\n"
                        + "\n".join(page_content)
                    )
                passages = review_summary_text("\n\n".join(pages))
                title = _summary_title(rows[0].document_name)
            else:
                title, passages = _generated_document_from_description(question)

            pdf_bytes = generate_pdf(title, passages)
            validate_pdf_bytes(pdf_bytes)
            filename = _safe_filename(title)
            send_email(
                to_email=current_user.email,
                subject=f"Your generated document: {title}",
                text=f"Your generated document, {title}, is attached.",
                pdf_bytes=pdf_bytes,
                filename=filename,
            )

            async def direct_pdf_response():
                yield "data: Your requested PDF was generated and sent to your email.\n\n"

            return StreamingResponse(
                direct_pdf_response(), media_type="text/event-stream"
            )
        except Exception as error:
            print(
                f"Direct PDF generation error: {type(error).__name__}: {error}"
            )

            error_message = (
                f"PDF generation failed: {type(error).__name__}: {error}"
            )

            async def direct_pdf_error(message: str = error_message):
                yield "event: error\n"
                yield f"data: {message}\n\n"

            return StreamingResponse(
                direct_pdf_error(), media_type="text/event-stream"
            )

    async def event_generator():
        try:
            inputs = {
                "messages": [HumanMessage(content=question)],
                "user_id": str(current_user.id),
                "user_email": current_user.email,
            }
            async for output in agent.astream(inputs):
                for value in output.values():
                    if "messages" in value:
                        msg = value["messages"][-1]
                        if getattr(msg, "name", None) == "generate_pdf_tool":
                            yield (
                                "data: Your requested PDF was generated and sent "
                                "to your email.\n\n"
                            )
                            continue
                        if getattr(msg, "type", None) != "ai":
                            continue
                        if getattr(msg, "tool_calls", None):
                            continue
                        if hasattr(msg, "content") and msg.content:
                            content = msg.content
                            if isinstance(content, list):
                                content = "".join(
                                    part.get("text", "")
                                    for part in content
                                    if isinstance(part, dict)
                                )
                            if content:
                                yield f"data: {content}\n\n"
        except Exception as error:
            error_text = str(error)
            print(f"Chat agent error: {type(error).__name__}: {error_text}")
            if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                message = (
                    "The AI provider quota is exhausted. "
                    "Please try again later or configure a billing-enabled API key."
                )
            else:
                message = "The document assistant could not complete this request."
            yield "event: error\n"
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)