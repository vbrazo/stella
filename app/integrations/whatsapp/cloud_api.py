"""Meta WhatsApp Cloud API provider."""

import logging

import httpx

from app.config import settings
from app.integrations.whatsapp.base import WhatsAppProvider
from app.integrations.whatsapp.models import InteractiveButton, InteractiveCard

logger = logging.getLogger(__name__)


class CloudAPIProvider(WhatsAppProvider):
    def __init__(self):
        self._base_url = f"https://graph.facebook.com/{settings.whatsapp_api_version}"
        self._phone_id = settings.whatsapp_phone_number_id
        self._token = settings.whatsapp_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _messages_url(self) -> str:
        return f"{self._base_url}/{self._phone_id}/messages"

    async def send_text(self, phone: str, text: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }
        return await self._send(payload)

    async def send_buttons(
        self, phone: str, body_text: str, buttons: list[InteractiveButton]
    ) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b.id, "title": b.title[:20]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }
        return await self._send(payload)

    async def send_cta_card(self, phone: str, card: InteractiveCard) -> dict:
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
        return await self._send(payload)

    async def download_media(self, media_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            url_resp = await client.get(
                f"{self._base_url}/{media_id}", headers=self._headers()
            )
            url_resp.raise_for_status()
            media_url = url_resp.json()["url"]

            media_resp = await client.get(media_url, headers=self._headers())
            media_resp.raise_for_status()
            return media_resp.content

    async def mark_as_read(self, message_id: str) -> None:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        await self._send(payload)

    async def _send(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self._messages_url(), json=payload, headers=self._headers()
            )

            if response.status_code >= 400:
                logger.error(
                    "WhatsApp API error %d: %s", response.status_code, response.text
                )
                response.raise_for_status()

            return response.json()
