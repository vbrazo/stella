"""WhatsApp provider interface."""

from abc import ABC, abstractmethod

from app.integrations.whatsapp.models import InteractiveButton, InteractiveCard


class WhatsAppProvider(ABC):
    """Abstract interface for WhatsApp messaging providers."""

    @abstractmethod
    async def send_text(self, phone: str, text: str) -> dict: ...

    @abstractmethod
    async def send_buttons(
        self, phone: str, body_text: str, buttons: list[InteractiveButton]
    ) -> dict: ...

    @abstractmethod
    async def send_cta_card(self, phone: str, card: InteractiveCard) -> dict: ...

    @abstractmethod
    async def download_media(self, media_id: str) -> bytes: ...

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> None: ...
