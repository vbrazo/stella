import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

MAX_JSON_RETRIES = 2


class LLMProvider(ABC):
    @abstractmethod
    async def complete_text(
        self,
        system: str,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> str:
        """Generate a text completion."""
        ...

    @abstractmethod
    async def complete_json(
        self,
        system: str,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        """Generate a structured JSON completion matching the given Pydantic schema."""
        ...

    async def complete_json_safe(
        self,
        system: str,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        """complete_json with retry on parse/validation failure."""
        last_error: Exception | None = None
        temp = temperature
        for attempt in range(MAX_JSON_RETRIES + 1):
            try:
                return await self.complete_json(system, messages, schema, temp)
            except (ValidationError, ValueError, KeyError) as e:
                last_error = e
                logger.warning(
                    "JSON completion attempt %d/%d failed: %s",
                    attempt + 1,
                    MAX_JSON_RETRIES + 1,
                    e,
                )
                temp = max(0.1, temp - 0.1)
        raise last_error  # type: ignore[misc]
