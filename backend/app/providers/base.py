from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> str:
        raise NotImplementedError

    async def stream(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> AsyncIterator[str]:
        yield await self.complete(system_prompt, user_prompt, model, metadata)
