"""Agent 1 (Concierge): CRM lookup and contextual opening."""

import logging

from app.fsm.machine import Action, SendText, UpdateStage
from app.integrations.kommo.client import KommoClient
from app.llm import get_llm
from app.llm.prompts.concierge import OPENING_SYSTEM
from app.models.conversation import Conversation, ConversationStage
from app.models.lead import LeadOrigin

logger = logging.getLogger(__name__)


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    """Handle IDLE and OPENING_SENT stages."""

    if conversation.stage == ConversationStage.IDLE:
        return await _send_opening(conversation)

    if conversation.stage == ConversationStage.OPENING_SENT:
        # Lead responded to opening — transition to intent extraction
        return [UpdateStage(ConversationStage.AWAITING_INTENT)]

    return []


async def _send_opening(conversation: Conversation) -> list[Action]:
    """Look up lead in CRM and send personalized opening."""
    actions: list[Action] = []

    # Enrich from Kommo
    kommo = KommoClient()
    if kommo.configured:
        try:
            enrichment = await kommo.enrich_lead_from_contact(conversation.phone)
            if enrichment:
                conversation.lead_data.update(enrichment)
                if enrichment.get("linkedin_url"):
                    conversation.lead_data["origin"] = LeadOrigin.LINKEDIN_ADS
        except Exception:
            logger.exception("Kommo enrichment failed for %s", conversation.phone)

    # Build lead context for LLM
    lead_context = _build_lead_context(conversation)

    # Generate opening message
    llm = get_llm()
    opening_msg = await llm.complete_text(
        system=OPENING_SYSTEM.format(lead_context=lead_context),
        messages=[{"role": "user", "content": "Gere a mensagem de abertura."}],
        temperature=0.8,
    )

    actions.append(SendText(opening_msg.strip()))
    actions.append(UpdateStage(ConversationStage.OPENING_SENT))
    return actions


def _build_lead_context(conversation: Conversation) -> str:
    data = conversation.lead_data
    parts = []

    name = data.get("name")
    if name:
        parts.append(f"Nome: {name}")

    origin = data.get("origin", LeadOrigin.UNKNOWN)
    if origin == LeadOrigin.LINKEDIN_ADS:
        parts.append("Origem: LinkedIn Lead Gen (já temos LinkedIn na base)")
    elif origin == LeadOrigin.SITE:
        parts.append("Origem: Site da Strides")
    else:
        parts.append("Origem: desconhecida")

    email = data.get("email")
    if email:
        parts.append(f"Email: {email}")

    linkedin = data.get("linkedin_url")
    if linkedin:
        parts.append(f"LinkedIn: {linkedin}")

    return "\n".join(parts) if parts else "Nenhum dado prévio disponível."
