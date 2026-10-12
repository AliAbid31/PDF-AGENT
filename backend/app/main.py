import io
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.agent.graph import agent
from app.api import auth
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.models.document import DocumentChunk
from app.models.user import User
from app.services.azure_storage import azure_storage

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
    async def event_generator():
        inputs = {
            "messages": [HumanMessage(content=question)],
            "user_id": str(current_user.id),
        }
        async for output in agent.astream(inputs):
            for key, value in output.items():
                if "messages" in value:
                    msg = value["messages"][-1]
                    if hasattr(msg, "content") and msg.content:
                        yield f"data: {msg.content}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)