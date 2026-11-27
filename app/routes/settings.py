from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
router = APIRouter(prefix="/api/settings", tags=["settings"])
PROVIDERS = {"openai", "anthropic", "google"}
class SettingsInput(BaseModel):
    provider: str
    model: str = Field(min_length=1, max_length=120)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: str = Field(default="", max_length=500)
    owner_contact_url: str = Field(default="", max_length=1000)
@router.put("")
def save_settings(settings: SettingsInput, request: Request) -> dict:
    if settings.provider not in PROVIDERS:
        raise HTTPException(400, "Provider must be openai, anthropic, or google.")
    request.app.state.chat_settings = settings.model_dump()
    return {"provider": settings.provider, "model": settings.model, "configured": True, "owner_contact_url": settings.owner_contact_url}
@router.get("")
def get_settings(request: Request) -> dict:
    settings = getattr(request.app.state, "chat_settings", None)
    if not settings:
        return {"provider": None, "model": None, "configured": False, "owner_contact_url": ""}
    return {"provider": settings["provider"], "model": settings["model"], "configured": True, "owner_contact_url": settings["owner_contact_url"]}
