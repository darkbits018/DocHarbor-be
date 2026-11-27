import httpx

from app.config import CF_ACCOUNT_ID, CF_API_TOKEN, CF_EMBEDDING_MODEL


class EmbeddingConfigurationError(RuntimeError):
    pass


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        raise EmbeddingConfigurationError(
            "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env to create embeddings."
        )
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_EMBEDDING_MODEL}"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
            json={"text": texts},
        )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", {})
    vectors = result.get("data") or result.get("embeddings")
    if not vectors or len(vectors) != len(texts):
        raise RuntimeError("Cloudflare returned an unexpected embeddings response.")
    return [vector if isinstance(vector, list) else vector.get("embedding") for vector in vectors]
