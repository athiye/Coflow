import json
from typing import Any, AsyncIterator
import httpx
from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.mock_provider import MockProvider

class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    async def complete(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> str:
        if not settings.openai_api_key:
            return await MockProvider().complete(system_prompt, user_prompt, model, metadata)
        payload = {"model": model, "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}], "temperature": 0.1}
        headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.openai_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def stream(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> AsyncIterator[str]:
        if not settings.openai_api_key:
            async for x in MockProvider().stream(system_prompt, user_prompt, model, metadata):
                yield x
            return
        payload = {"model": model, "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}], "temperature":0.1, "stream":True}
        headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{settings.openai_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        payload = json.loads(data)
                        delta = payload["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue
