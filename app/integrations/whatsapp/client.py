import logging

import httpx

from app.config import settings
from app.integrations.whatsapp.models import InteractiveButton, InteractiveCard

logger = logging.getLogger(__name__)

BASE_URL = f"https://graph.facebook.com/{settings.whatsapp_api_version}"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }


def _messages_url() -> str:
    return f"{BASE_URL}/{settings.whatsapp_phone_number_id}/messages"


async def send_text(phone: str, text: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }
    return await _send(payload)


async def send_buttons(phone: str, body_text: str, buttons: list[InteractiveButton]) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b.id, "title": b.title[:20]}} for b in buttons[:3]
                ]
            },
        },
    }
    return await _send(payload)


async def send_cta_card(phone: str, card: InteractiveCard) -> dict:
    interactive: dict = {
        "type": "cta_url",
        "body": {"text": card.body_text},
        "action": {
            "name": "cta_url",
            "parameters": {
                "display_text": card.button_text[:20],
                "url": card.button_url,
            },
        },
    }

    if card.header_text:
        interactive["header"] = {"type": "text", "text": card.header_text}

    if card.footer_text:
        interactive["footer"] = {"text": card.footer_text}

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive,
    }
    return await _send(payload)


async def download_media(media_id: str) -> bytes:
    """Download media (audio) from WhatsApp by media ID."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Get media URL
        url_resp = await client.get(f"{BASE_URL}/{media_id}", headers=_headers())
        url_resp.raise_for_status()
        media_url = url_resp.json()["url"]

        # Step 2: Download actual file
        media_resp = await client.get(media_url, headers=_headers())
        media_resp.raise_for_status()
        return media_resp.content


async def mark_as_read(message_id: str) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    await _send(payload)


async def _send(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(_messages_url(), json=payload, headers=_headers())

        if response.status_code >= 400:
            logger.error("WhatsApp API error %d: %s", response.status_code, response.text)
            response.raise_for_status()

        return response.json()
