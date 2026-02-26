from app.config import settings
from app.llm.base import LLMProvider

_instance: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _instance
    if _instance is not None:
        return _instance

    if settings.llm_provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        _instance = AnthropicProvider()
    else:
        from app.llm.openai_provider import OpenAIProvider

        _instance = OpenAIProvider()

    return _instance
