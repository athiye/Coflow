from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = 'anthropic'

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.anthropic_base_url).rstrip('/')
        self.api_key = api_key or settings.anthropic_api_key

    async def complete(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> str:
        if not self.api_key:
            from app.providers.mock_provider import MockProvider
            return await MockProvider().complete(system_prompt, user_prompt, model, metadata)
        payload = {
            'model': model,
            'max_tokens': 1400,
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': user_prompt}],
        }
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(f'{self.base_url}/messages', headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
            blocks = data.get('content', [])
            return '\n'.join(block.get('text', '') for block in blocks if block.get('type') == 'text').strip()
        except Exception:
            from app.providers.mock_provider import MockProvider
            return await MockProvider().complete(system_prompt, user_prompt, model, metadata)
