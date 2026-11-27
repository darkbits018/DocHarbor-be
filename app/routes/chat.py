from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.ai.graph import chat_graph
from app.database import get_db
router = APIRouter(prefix="/api/chat", tags=["chat"])
class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
@router.post("")
def chat(payload: ChatInput, request: Request, db: Session = Depends(get_db)) -> dict:
    settings = getattr(request.app.state, "chat_settings", None)
    if not settings:
        raise HTTPException(400, "Configure a chat provider in Settings before asking questions.")
    try:
        result = chat_graph.invoke({"question": payload.question, "evidence": [], "answer": "", "provider": settings["provider"], "model": settings["model"], "api_key": settings["api_key"], "base_url": settings["base_url"], "db": db})
    except Exception as exc:
        raise HTTPException(502, "Chat or retrieval provider failed. Check provider credentials and service availability.") from exc
    sources = []
    for item in result.get("evidence", []):
        source = {"document_name": item["document_name"], "reference": item["reference"], "excerpt": item["text"]}
        if source not in sources:
            sources.append(source)
    return {"answer": result["answer"], "sources": sources}
