from app.providers.mock_provider import MockProvider
from app.providers.openai_responses import OpenAIResponsesProvider


class ProviderFactory:
    @staticmethod
    def get(provider_name: str):
        if provider_name in {"openai_responses", "openai_compatible"}:
            return OpenAIResponsesProvider()
        return MockProvider()