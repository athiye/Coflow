from typing import Any, AsyncIterator
from app.providers.base import LLMProvider

class MockProvider(LLMProvider):
    name = "mock"

    async def complete(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> str:
        text = user_prompt.lower()
        if any(x in text for x in ["architecture","onboarding","roadmap","release","product manager","repo","refactor"]):
            return (
                "PLAN:\n"
                "1. List files in the repository\n"
                "2. Read likely entry points and key runtime files\n"
                "3. Synthesize a structured answer\n\n"
                "ACTIONS:\n"
                "tool:list_files confidence:0.9 args:{}\n\n"
                "ANSWER:\n"
                "I will start by listing the files in the repository to identify key runtime modules."
            )
        if any(x in text for x in ["debug","bug","summarize",".py",".js",".ts"]):
            return (
                "PLAN:\n"
                "1. Inspect the relevant file\n"
                "2. Make the smallest safe change or explanation\n"
                "3. Summarize the impact\n\n"
                "ACTIONS:\n"
                "tool:read_file confidence:1 args:{}\n\n"
                "ANSWER:\n"
                "Reading the relevant file."
            )
        return "PLAN:\n1. Analyze request\n2. Return focused answer\n\nACTIONS:\n\nANSWER:\nHere is a concise engineering response."

    async def stream(self, system_prompt: str, user_prompt: str, model: str, metadata: dict[str, Any] | None = None) -> AsyncIterator[str]:
        text = await self.complete(system_prompt, user_prompt, model, metadata)
        for chunk in text.split(" "):
            yield chunk + " "
