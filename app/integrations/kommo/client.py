import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class KommoClient:
    def __init__(self):
        self.base_url = settings.kommo_base_url
        self.token = settings.kommo_api_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @property
    def configured(self) -> bool:
        return bool(self.token)

    async def search_contact_by_phone(self, phone: str) -> dict | None:
        """Search for a contact in Kommo by phone number."""
        if not self.configured:
            return None

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/v4/contacts",
                params={"query": phone},
                headers=self._headers(),
            )
            if response.status_code != 200:
                logger.error("Kommo search failed: %d %s", response.status_code, response.text)
                return None

            data = response.json()
            contacts = data.get("_embedded", {}).get("contacts", [])
            return contacts[0] if contacts else None

    async def get_lead_by_contact(self, contact_id: int) -> dict | None:
        """Get leads associated with a contact."""
        if not self.configured:
            return None

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/v4/contacts/{contact_id}",
                params={"with": "leads"},
                headers=self._headers(),
            )
            if response.status_code != 200:
                return None

            contact = response.json()
            leads = contact.get("_embedded", {}).get("leads", [])
            return leads[0] if leads else None

    async def add_note(self, entity_type: str, entity_id: int, text: str) -> dict | None:
        """Add a note to a lead or contact."""
        if not self.configured:
            return None

        payload = [{"note_type": "common", "params": {"text": text}}]
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/api/v4/{entity_type}/{entity_id}/notes",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code >= 400:
                logger.error("Kommo add_note failed: %d %s", response.status_code, response.text)
                return None
            return response.json()

    async def update_lead_tags(self, lead_id: int, tags: list[str]) -> dict | None:
        """Update tags on a lead."""
        if not self.configured:
            return None

        payload = [{"id": lead_id, "_embedded": {"tags": [{"name": t} for t in tags]}}]
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.patch(
                f"{self.base_url}/api/v4/leads",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code >= 400:
                logger.error("Kommo update_tags failed: %d %s", response.status_code, response.text)
                return None
            return response.json()

    async def update_lead_custom_fields(self, lead_id: int, fields: list[dict]) -> dict | None:
        """Update custom fields on a lead."""
        if not self.configured:
            return None

        payload = [{"id": lead_id, "custom_fields_values": fields}]
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.patch(
                f"{self.base_url}/api/v4/leads",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code >= 400:
                logger.error("Kommo update fields failed: %d %s", response.status_code, response.text)
                return None
            return response.json()

    async def enrich_lead_from_contact(self, phone: str) -> dict:
        """Search contact by phone and extract enrichment data."""
        contact = await self.search_contact_by_phone(phone)
        if not contact:
            return {}

        result = {
            "kommo_contact_id": contact.get("id"),
            "name": contact.get("name"),
        }

        # Extract custom fields
        for field in contact.get("custom_fields_values", []):
            code = field.get("field_code", "")
            values = field.get("values", [])
            if not values:
                continue
            val = values[0].get("value", "")
            if code == "EMAIL":
                result["email"] = val
            elif code == "PHONE":
                result["phone"] = val
            elif field.get("field_name", "").lower() == "linkedin":
                result["linkedin_url"] = val

        # Get associated lead
        lead = await self.get_lead_by_contact(contact["id"])
        if lead:
            result["kommo_lead_id"] = lead.get("id")

        return result
