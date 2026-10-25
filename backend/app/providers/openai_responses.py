import json
from typing import Any, AsyncIterator
import httpx

from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.mock_provider import MockProvider


class OpenAIResponsesProvider(LLMProvider):
    name = "openai_responses"

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if not settings.openai_api_key:
            return await MockProvider().complete(system_prompt, user_prompt, model, metadata)

        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        }

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/responses",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        output_text = data.get("output_text")
        if output_text:
            return output_text

        text_parts: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    text_parts.append(content.get("text", ""))
        return "\n".join(part for part in text_parts if part).strip()

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        if not settings.openai_api_key:
            async for chunk in MockProvider().stream(system_prompt, user_prompt, model, metadata):
                yield chunk
            return

        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.openai_base_url.rstrip('/')}/responses",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        evt = json.loads(data)
                    except Exception:
                        continue

                    evt_type = evt.get("type", "")
                    if evt_type == "response.output_text.delta":
                        delta = evt.get("delta") or ""
                        if delta:
                            yield delta
