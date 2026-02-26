import json
import logging

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.config import settings
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def complete_text(
        self,
        system: str,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=messages,
            temperature=temperature,
        )
        return response.content[0].text

    async def complete_json(
        self,
        system: str,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        json_schema = schema.model_json_schema()
        schema_instruction = (
            f"\n\nYou MUST respond with ONLY valid JSON (no markdown, no explanation) matching this schema:\n"
            f"{json.dumps(json_schema, indent=2)}"
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system + schema_instruction,
            messages=messages,
            temperature=temperature,
        )

        content = response.content[0].text
        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        return schema.model_validate_json(content)
