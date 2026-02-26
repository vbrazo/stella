"""Lead enrichment service: CRM lookup + LinkedIn scraping + qualification."""

import logging

from app.integrations.kommo.client import KommoClient
from app.integrations.linkedin.client import LinkedInScraperClient
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


async def enrich_lead(conversation: Conversation) -> None:
    """Enrich conversation lead data from CRM and LinkedIn."""
    data = conversation.lead_data

    # Step 1: CRM enrichment (already done in opening, but may need refresh)
    if not data.get("kommo_contact_id"):
        kommo = KommoClient()
        if kommo.configured:
            try:
                enrichment = await kommo.enrich_lead_from_contact(conversation.phone)
                if enrichment:
                    data.update(enrichment)
            except Exception:
                logger.exception("Kommo enrichment failed")

    # Step 2: LinkedIn scraping (if URL available and not yet scraped)
    linkedin_url = data.get("linkedin_url")
    if linkedin_url and not data.get("scraped_data"):
        scraper = LinkedInScraperClient()
        if scraper.configured:
            try:
                raw = await scraper.scrape(linkedin_url)
                if raw:
                    profile = scraper.extract_profile_data(raw)
                    data["scraped_data"] = raw
                    data["name"] = profile.get("name") or data.get("name")
                    data["role"] = profile.get("role") or data.get("role")
                    data["company"] = profile.get("company") or data.get("company")

                    # Infer seniority from role
                    data["seniority"] = _infer_seniority(profile.get("role", ""))
            except Exception:
                logger.exception("LinkedIn scrape failed for %s", linkedin_url)


def _infer_seniority(role: str) -> str:
    """Infer seniority level from job title."""
    role_lower = role.lower()

    c_level_signals = ["cto", "cdo", "cio", "ceo", "vp", "vice president", "chief"]
    director_signals = ["director", "diretor", "diretora"]
    head_signals = ["head", "head de", "senior manager", "gerente sênior", "gerente senior"]
    manager_signals = ["manager", "gerente", "coordenador", "lead", "tech lead"]

    if any(s in role_lower for s in c_level_signals):
        return "c_level"
    if any(s in role_lower for s in director_signals):
        return "director"
    if any(s in role_lower for s in head_signals):
        return "head"
    if any(s in role_lower for s in manager_signals):
        return "manager"
    return "unknown"
