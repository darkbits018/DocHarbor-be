import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk

logger = logging.getLogger(__name__)


def search_chunks(db: Session, query_embedding: list[float], limit: int = 5) -> list[dict]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    rows = db.execute(
        select(DocumentChunk, Document.filename, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    ).all()
    results = [
        {
            "document_name": filename,
            "reference": chunk.source_reference,
            "text": chunk.content,
            "distance": float(distance_value),
        }
        for chunk, filename, distance_value in rows
    ]
    logger.info(
        "Retrieval complete: candidates=%d requested_limit=%d",
        len(results), limit,
    )
    for rank, item in enumerate(results, start=1):
        logger.info(
            "Retrieval candidate #%d document=%r reference=%r cosine_distance=%.4f chunk_chars=%d",
            rank, item["document_name"], item["reference"],
            item["distance"], len(item["text"]),
        )
    return results
