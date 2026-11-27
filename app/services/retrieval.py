from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk


def search_chunks(db: Session, query_embedding: list[float], limit: int = 5) -> list[dict]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    rows = db.execute(
        select(DocumentChunk, Document.filename, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    ).all()
    return [
        {
            "document_name": filename,
            "reference": chunk.source_reference,
            "text": chunk.content,
            "distance": float(distance_value),
        }
        for chunk, filename, distance_value in rows
    ]
