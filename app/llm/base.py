from abc import ABC, abstractmethod

from pydantic import BaseModel


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
