import io
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
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
from app.services.pdf_engine import generate_pdf

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")


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
        text_content = page.extract_text()
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
    )

    if is_pdf_resume_request:
        try:
            db = SessionLocal()
            try:
                rows = db.execute(
                    text(
                        """
                        SELECT document_name, page_number, content
                        FROM document_chunks
                        WHERE user_id = :uid
                        ORDER BY page_number, id
                        """
                    ),
                    {"uid": str(current_user.id)},
                ).fetchall()
            finally:
                db.close()

            if not rows:
                raise RuntimeError(
                    "No indexed PDF content was found for the authenticated user."
                )

            passages = "\n\n".join(
                f"[{row.document_name} | Page {row.page_number}]\n{row.content}"
                for row in rows
            )

            pdf_bytes = generate_pdf("Course Resume", passages)
            send_email(
                to_email=current_user.email,
                subject="Your Course Resume",
                text="Your course resume is attached.",
                pdf_bytes=pdf_bytes,
                filename="Course_Resume.pdf",
            )

            async def direct_pdf_response():
                yield "data: Your PDF summary was generated and sent to your email.\n\n"

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
                                "data: Your PDF summary was generated and sent "
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