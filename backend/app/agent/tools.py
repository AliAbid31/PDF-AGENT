from typing import Annotated
import re

from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.prebuilt import InjectedState
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.config import settings
from app.services.email_service import send_email
from app.services.pdf_engine import generate_pdf

@tool
def search_document(
    query: str, user_id: Annotated[str, InjectedState("user_id")]
):
    """Searches for relevant passages in the PDFs uploaded by the user."""
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        api_key=settings.GEMINI_API_KEY
    )
    query_vector = embeddings.embed_query(query)
    db = SessionLocal()
    try:
        is_summary = any(
            word in query.casefold()
            for word in (
                "summary",
                "summarize",
                "resume",
                "résumé",
                "synthesis",
                "entire document",
                "whole document",
                "all pages",
            )
        )
        limit = 80 if is_summary else 12
        order = (
            "document_name, page_number, id"
            if is_summary
            else "embedding <=> CAST(:vec AS vector)"
        )
        sql = text(
            f"""
                SELECT document_name, page_number, content
                FROM document_chunks
                WHERE user_id = :uid
                ORDER BY {order}
                LIMIT :limit;
            """
        )
        result = db.execute(
            sql,
            {"vec": query_vector, "uid": user_id, "limit": limit},
        ).fetchall()
        if not result:
            return "No relevant passages found."
        return "\n\n".join(
            [f"[Doc: {r[0]} | Page {r[1]}]: {r[2]}" for r in result]
        )
    finally:
        db.close()

@tool
def generate_pdf_tool(
    document_title: str,
    content: str,
    user_email: Annotated[str, InjectedState("user_email")],
):
    """Generates a PDF from the summarized document content and emails it to the current user."""
    pdf_bytes = generate_pdf(document_title, content)
    safe_title = re.sub(r"[^\w\s-]", "", document_title, flags=re.UNICODE)
    safe_title = re.sub(r"[\s-]+", "_", safe_title).strip("_")[:120]
    filename = f"{safe_title or 'Generated_Document'}.pdf"
    send_email(
        to_email=user_email,
        subject=f"Your generated document: {document_title}",
        text=f"Please find attached: {document_title}.",
        pdf_bytes=pdf_bytes,
        filename=filename
    )
    return "PDF generated and sent to your email."