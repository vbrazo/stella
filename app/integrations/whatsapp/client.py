"""WhatsApp client factory.

Maintains backward-compatible module-level functions by delegating to the
configured provider instance. All existing imports like:

    from app.integrations.whatsapp import client as wa_client
    await wa_client.send_text(phone, text)

continue to work without changes.
"""

from app.integrations.whatsapp.base import WhatsAppProvider
from app.integrations.whatsapp.models import InteractiveButton, InteractiveCard

_provider: WhatsAppProvider | None = None


def _get_provider() -> WhatsAppProvider:
    global _provider
    if _provider is not None:
        return _provider

    from app.config import settings

    if settings.whatsapp_provider == "evolution":
        from app.integrations.whatsapp.evolution_api import EvolutionAPIProvider

        _provider = EvolutionAPIProvider()
    else:
        from app.integrations.whatsapp.cloud_api import CloudAPIProvider

        _provider = CloudAPIProvider()

    return _provider


async def send_text(phone: str, text: str) -> dict:
    return await _get_provider().send_text(phone, text)


async def send_buttons(
    phone: str, body_text: str, buttons: list[InteractiveButton]
) -> dict:
    return await _get_provider().send_buttons(phone, body_text, buttons)


async def send_cta_card(phone: str, card: InteractiveCard) -> dict:
    return await _get_provider().send_cta_card(phone, card)


async def download_media(media_id: str) -> bytes:
    return await _get_provider().download_media(media_id)


async def mark_as_read(message_id: str) -> None:
    return await _get_provider().mark_as_read(message_id)
