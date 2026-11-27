import httpx

PROVIDERS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
}

async def generate_answer(provider: str, model: str, api_key: str, messages: list[dict], base_url: str = "") -> str:
    if provider not in PROVIDERS:
        raise ValueError("Unsupported chat provider")
    if provider == "anthropic":
        body = {"model": model, "max_tokens": 900, "system": messages[0]["content"], "messages": messages[1:]}
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        url = base_url or PROVIDERS[provider]
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return "".join(part.get("text", "") for part in response.json().get("content", []))
    url = base_url or PROVIDERS[provider]
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, headers=headers, json={"model": model, "messages": messages, "temperature": 0})
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
