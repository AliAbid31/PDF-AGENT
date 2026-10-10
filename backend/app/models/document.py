import uuid
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    document_name = Column(String, nullable=False)
    page_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # Embeddings text-embedding-3-small font 1536 dimensions
    embedding = Column(Vector(1536), nullable=False)