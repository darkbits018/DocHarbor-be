import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSettings
from app.services.security import SettingsEncryptionError, encrypt_api_key

router = APIRouter(prefix="/api/settings", tags=["settings"])
PROVIDERS = {"openai", "anthropic", "google", "groq", "openrouter"}
FREE_LIMITS = {
    "groq": "Free developer tier. Exact limits depend on account and model; check Groq Console → Limits.",
    "openrouter": "Free variants currently have 20 requests/minute and 50/day on the free plan; upstream limits also apply.",
    "google": "Gemini API free tier is model/account-specific; check Google AI Studio for your quota.",
    "openai": "No general free API tier; usage is billed according to the selected model.",
    "anthropic": "No general free API tier; usage is billed according to the selected model.",
}

class SettingsInput(BaseModel):
    provider: str
    model: str = Field(min_length=1, max_length=120)
    api_key: str | None = Field(default=None, max_length=500)
    base_url: str = Field(default="", max_length=500)
    owner_contact_url: str = Field(default="", max_length=1000)

class ModelCatalogInput(BaseModel):
    provider: str
    api_key: str = Field(min_length=1, max_length=500)

@router.post("/models")
async def list_models(payload: ModelCatalogInput) -> dict:
    if payload.provider not in PROVIDERS:
        raise HTTPException(400, "Unsupported provider.")
    headers = {"Authorization": f"Bearer {payload.api_key}"}
    timeout = httpx.Timeout(20)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if payload.provider == "openrouter":
                response = await client.get("https://openrouter.ai/api/v1/models", headers=headers, params={"output_modalities": "text"})
                response.raise_for_status()
                raw = response.json().get("data", [])
                models = []
                for item in raw:
                    pricing = item.get("pricing", {})
                    free = item.get("id", "").endswith(":free") or (float(pricing.get("prompt", 1) or 0) == 0 and float(pricing.get("completion", 1) or 0) == 0)
                    if free and "text" in item.get("architecture", {}).get("output_modalities", ["text"]):
                        models.append({"id": item["id"], "name": item.get("name", item["id"]), "free": True})
                models.insert(0, {"id": "openrouter/free", "name": "OpenRouter free model router", "free": True})
                return {"models": models, "free_limit": FREE_LIMITS[payload.provider], "limit_source": "Live models/pricing from OpenRouter; public plan cap."}
            if payload.provider == "groq":
                response = await client.get("https://api.groq.com/openai/v1/models", headers=headers)
                response.raise_for_status()
                models = [{"id": item["id"], "name": item.get("id", ""), "free": True} for item in response.json().get("data", []) if item.get("active", True) and item.get("id") not in {"whisper-large-v3", "whisper-large-v3-turbo"}]
                return {"models": models, "free_limit": FREE_LIMITS[payload.provider], "limit_source": "Groq publishes general limits; exact quota is account-specific."}
            if payload.provider == "google":
                response = await client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": payload.api_key})
                response.raise_for_status()
                free_ids = {"gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"}
                models = []
                for item in response.json().get("models", []):
                    model_id = item.get("name", "").removeprefix("models/")
                    if model_id in free_ids and "generateContent" in item.get("supportedGenerationMethods", []):
                        models.append({"id": model_id, "name": item.get("displayName", model_id), "free": True})
                return {"models": models, "free_limit": FREE_LIMITS[payload.provider], "limit_source": "Model list is live; free-tier eligibility is a maintained catalog and may vary by account."}
            raise HTTPException(400, "Live free model discovery is available for Google Gemini, Groq, and OpenRouter.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, "Provider rejected the API key or model catalog request.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Could not reach the provider model catalog.") from exc

@router.put("")
def save_settings(settings: SettingsInput, db: Session = Depends(get_db)) -> dict:
    if settings.provider not in PROVIDERS:
        raise HTTPException(400, "Provider must be openai, anthropic, google, groq, or openrouter.")
    saved = db.get(AppSettings, 1)
    if not settings.api_key and (saved is None or saved.provider != settings.provider):
        raise HTTPException(400, "Enter the provider API key to configure or change the provider.")
    try:
        if saved is None:
            saved = AppSettings(
                id=1,
                provider=settings.provider,
                model=settings.model,
                encrypted_api_key=encrypt_api_key(settings.api_key or ""),
                base_url=settings.base_url,
                owner_contact_url=settings.owner_contact_url,
            )
            db.add(saved)
        else:
            saved.provider = settings.provider
            saved.model = settings.model
            saved.base_url = settings.base_url
            saved.owner_contact_url = settings.owner_contact_url
            if settings.api_key:
                saved.encrypted_api_key = encrypt_api_key(settings.api_key)
        db.commit()
    except SettingsEncryptionError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc
    return {"provider": settings.provider, "model": settings.model, "configured": True, "owner_contact_url": settings.owner_contact_url}

@router.get("")
def get_settings(db: Session = Depends(get_db)) -> dict:
    settings = db.get(AppSettings, 1)
    if not settings:
        return {"provider": None, "model": None, "configured": False, "api_key_saved": False, "base_url": "", "owner_contact_url": ""}
    return {
        "provider": settings.provider,
        "model": settings.model,
        "configured": True,
        "api_key_saved": bool(settings.encrypted_api_key),
        "base_url": settings.base_url,
        "owner_contact_url": settings.owner_contact_url,
    }
