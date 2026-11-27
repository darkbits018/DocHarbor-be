import logging
import httpx
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, UPLOAD_DIR
from app.services.embeddings import EmbeddingConfigurationError, embed_texts
from app.database import get_db
from app.models import Document, DocumentChunk
from app.schemas import DocumentSummary
from app.services.chunking import chunk_sections
from app.services.extraction import extract_sections

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentSummary:
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Only PDF, DOCX, and TXT files are supported.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
    if extension == ".txt":
        try:
            data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, "TXT files must use UTF-8 encoding.") from exc
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = UPLOAD_DIR / f"{uuid4().hex}{extension}"
    stored.write_bytes(data)
    try:
        chunks = chunk_sections(extract_sections(stored, extension))
        if not chunks:
            raise HTTPException(422, "No readable text was found in this document.")
        document = Document(filename=filename[:255], stored_path=stored.name, file_type=extension)
        vectors = await embed_texts([body for body, _ in chunks])
        document.chunks = [
            DocumentChunk(chunk_index=i, content=body, source_reference=ref, embedding=vectors[i])
            for i, (body, ref) in enumerate(chunks)
        ]
        db.add(document)
        db.commit()
        db.refresh(document)
        return DocumentSummary(id=document.id, filename=document.filename, file_type=document.file_type, uploaded_at=document.uploaded_at, chunk_count=len(chunks))
    except HTTPException:
        stored.unlink(missing_ok=True)
        raise
    except IntegrityError as exc:
        db.rollback()
        stored.unlink(missing_ok=True)
        raise HTTPException(409, "A document with this filename is already uploaded.") from exc
    except Exception as exc:
        db.rollback()
        stored.unlink(missing_ok=True)
        logger.exception("Could not process uploaded file")
        if isinstance(exc, httpx.HTTPError):
            raise HTTPException(502, "Cloudflare embedding request failed.") from exc
        if isinstance(exc, EmbeddingConfigurationError):
            raise HTTPException(503, str(exc)) from exc
        raise HTTPException(422, "Could not read this file. Check that it is a valid, text-based document.") from exc

@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentSummary]:
    docs = db.scalars(select(Document).order_by(Document.uploaded_at.desc())).all()
    return [DocumentSummary(id=d.id, filename=d.filename, file_type=d.file_type, uploaded_at=d.uploaded_at, chunk_count=len(d.chunks)) for d in docs]

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found.")
    stored = (UPLOAD_DIR / Path(document.stored_path).name).resolve()
    if UPLOAD_DIR not in stored.parents:
        raise HTTPException(500, "Stored document path is invalid.")
    db.delete(document)
    db.commit()
    stored.unlink(missing_ok=True)
