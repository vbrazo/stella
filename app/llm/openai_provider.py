import json
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def complete_text(
        self,
        system: str,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> str:
        all_messages = [{"role": "system", "content": system}] + messages

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def complete_json(
        self,
        system: str,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        json_schema = schema.model_json_schema()
        schema_instruction = (
            f"\n\nYou MUST respond with valid JSON matching this schema:\n{json.dumps(json_schema, indent=2)}"
        )

        all_messages = [{"role": "system", "content": system + schema_instruction}] + messages

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return schema.model_validate_json(content)
