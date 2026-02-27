"""Evolution API v2 WhatsApp provider."""

import base64
import logging

import httpx

from app.config import settings
from app.integrations.whatsapp.base import WhatsAppProvider
from app.integrations.whatsapp.models import InteractiveButton, InteractiveCard

logger = logging.getLogger(__name__)


class EvolutionAPIProvider(WhatsAppProvider):
    def __init__(self):
        self._base_url = settings.evolution_api_url.rstrip("/")
        self._api_key = settings.evolution_api_key
        self._instance = settings.evolution_instance_name

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._api_key,
            "Content-Type": "application/json",
        }

    async def send_text(self, phone: str, text: str) -> dict:
        payload = {"number": phone, "text": text}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._base_url}/message/sendText/{self._instance}",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def send_buttons(
        self, phone: str, body_text: str, buttons: list[InteractiveButton]
    ) -> dict:
        payload = {
            "number": phone,
            "title": "",
            "description": body_text,
            "buttons": [
                {"type": "reply", "displayText": b.title[:20], "id": b.id}
                for b in buttons[:3]
            ],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._base_url}/message/sendButtons/{self._instance}",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def send_cta_card(self, phone: str, card: InteractiveCard) -> dict:
        # Evolution API v2 may not support CTA cards natively; fallback to text+link
        parts = []
        if card.header_text:
            parts.append(f"*{card.header_text}*")
        parts.append(card.body_text)
        parts.append(f"{card.button_text}: {card.button_url}")
        text = "\n\n".join(parts)
        return await self.send_text(phone, text)

    async def download_media(self, media_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self._base_url}/chat/getBase64FromMediaMessage/{self._instance}",
                params={"messageId": media_id},
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return base64.b64decode(data.get("base64", ""))

    async def mark_as_read(self, message_id: str) -> None:
        payload = {"readMessages": [{"id": message_id}]}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(
                f"{self._base_url}/chat/markMessageAsRead/{self._instance}",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code >= 400:
                logger.warning(
                    "Evolution mark_as_read failed: %d", response.status_code
                )
