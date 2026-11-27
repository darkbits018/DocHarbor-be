import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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


@router.get("/history")
def get_chat_history(db: Session = Depends(get_db)) -> dict:
    thread = db.get(ChatThread, 1)
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
    thread = db.get(ChatThread, 1)
    if thread is None:
        thread = ChatThread(id=1, title=payload.question[:200])
        db.add(thread)
        db.flush()
    db.add_all([
        ChatMessage(thread_id=thread.id, role="user", content=payload.question),
        ChatMessage(thread_id=thread.id, role="assistant", content=answer, sources=sources),
    ])
    db.commit()
    return {"answer": answer, "sources": sources}
import logging
import time
