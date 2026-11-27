import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.ai.graph import chat_graph
from app.ai.prompts import UNSUPPORTED_ANSWER
from app.database import get_db
from app.models import AppSettings, ChatMessage, ChatThread
from app.services.security import SettingsEncryptionError, decrypt_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    thread_id: int | None = None


class ThreadUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    is_pinned: bool | None = None
    is_archived: bool | None = None


@router.get("/threads")
def list_threads(db: Session = Depends(get_db)) -> list[dict]:
    threads = db.query(ChatThread).filter(ChatThread.is_archived.is_(False)).order_by(ChatThread.is_pinned.desc(), ChatThread.created_at.desc(), ChatThread.id.desc()).all()
    return [{"id": thread.id, "title": thread.title, "is_pinned": thread.is_pinned} for thread in threads]


@router.patch("/threads/{thread_id}")
def update_thread(thread_id: int, payload: ThreadUpdate, db: Session = Depends(get_db)) -> dict:
    thread = db.get(ChatThread, thread_id)
    if thread is None:
        raise HTTPException(404, "Chat thread not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(thread, field, value)
    db.commit()
    return {"id": thread.id, "title": thread.title, "is_pinned": thread.is_pinned, "is_archived": thread.is_archived}


@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: int, db: Session = Depends(get_db)) -> None:
    thread = db.get(ChatThread, thread_id)
    if thread is None:
        raise HTTPException(404, "Chat thread not found.")
    db.delete(thread)
    db.commit()


@router.post("/threads")
def create_thread(db: Session = Depends(get_db)) -> dict:
    next_id = (db.scalar(select(func.max(ChatThread.id))) or 0) + 1
    thread = ChatThread(id=next_id, title="New chat")
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return {"id": thread.id, "title": thread.title}


@router.get("/threads/{thread_id}")
def get_chat_history(thread_id: int, db: Session = Depends(get_db)) -> dict:
    thread = db.get(ChatThread, thread_id)
    if thread is None:
        return {"thread_id": None, "messages": []}
    return {
        "thread_id": thread.id,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "text": message.content,
                "sources": message.sources or [],
                "created_at": message.created_at,
            }
            for message in sorted(thread.messages, key=lambda item: item.id)
        ],
    }


@router.post("")
def chat(payload: ChatInput, db: Session = Depends(get_db)) -> dict:
    started = time.perf_counter()
    logger.info("Chat request received: question_chars=%d", len(payload.question))
    settings = db.get(AppSettings, 1)
    if not settings:
        logger.warning("Chat request rejected: provider settings are missing")
        raise HTTPException(400, "Configure a chat provider in Settings before asking questions.")
    try:
        api_key = decrypt_api_key(settings.encrypted_api_key)
        result = chat_graph.invoke({"question": payload.question, "evidence": [], "answer": "", "provider": settings.provider, "model": settings.model, "api_key": api_key, "base_url": settings.base_url, "db": db})
    except Exception as exc:
        logger.exception(
            "Chat pipeline failed: provider=%s model=%s",
            settings.provider, settings.model,
        )
        if isinstance(exc, SettingsEncryptionError):
            raise HTTPException(503, str(exc)) from exc
        raise HTTPException(502, "Chat or retrieval provider failed. Check provider credentials and service availability.") from exc
    answer = result["answer"]
    sources = []
    # Retrieved chunks are citations only when the answer itself was accepted.
    evidence = result.get("evidence", []) if answer != UNSUPPORTED_ANSWER else []
    seen_references = set()
    for item in evidence:
        reference_key = (item["document_name"], item["reference"])
        if reference_key in seen_references:
            continue
        seen_references.add(reference_key)
        source = {"document_name": item["document_name"], "reference": item["reference"], "excerpt": item["text"]}
        sources.append(source)
    logger.info(
        "Chat request completed: outcome=%s source_count=%d elapsed_ms=%.1f",
        "supported" if sources else "unsupported", len(sources),
        (time.perf_counter() - started) * 1000,
    )
    thread = db.get(ChatThread, payload.thread_id) if payload.thread_id else None
    if payload.thread_id and thread is None:
        raise HTTPException(404, "Chat thread not found.")
    if thread is None:
        next_id = (db.scalar(select(func.max(ChatThread.id))) or 0) + 1
        thread = ChatThread(id=next_id, title=payload.question[:200])
        db.add(thread)
        db.flush()
    elif thread.title == "New chat":
        thread.title = payload.question[:200]
    db.add_all([
        ChatMessage(thread_id=thread.id, role="user", content=payload.question),
        ChatMessage(thread_id=thread.id, role="assistant", content=answer, sources=sources),
    ])
    db.commit()
    return {"answer": answer, "sources": sources}
import logging
import time
