"""Agent 1 (Concierge): Intent extraction from lead's open response.

Classifies the lead's intent into 4 clusters with confidence scores.
If confident -> moves to confirmation. If ambiguous -> delegates to Agent 2 (Qualifier) for Q1.
"""

import logging

from app.engine.classifier import classify_intent, get_dominant_cluster
from app.fsm.handlers.qualifier import ask_q1
from app.fsm.machine import Action, UpdateStage
from app.llm import get_llm
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    if conversation.stage != ConversationStage.AWAITING_INTENT:
        return []

    return await _extract_intent(conversation, message_text)


async def _extract_intent(conversation: Conversation, message_text: str) -> list[Action]:
    """Run intent classification on the lead's open response."""
    llm = get_llm()
    lead_context = _lead_context_str(conversation)

    analysis = await classify_intent(llm, message_text, lead_context)

    # Store scores
    conversation.cluster_scores = analysis.cluster_scores.model_dump()
    conversation.lead_data["ai_interest"] = analysis.ai_interest
    conversation.lead_data["urgency"] = analysis.urgency

    # Check for price request -> price fallback
    if analysis.price_request:
        return [UpdateStage(ConversationStage.PRICE_FALLBACK)]

    # Check if cluster is clear enough for confirmation
    dominant, confidence, is_ambiguous = get_dominant_cluster(analysis.cluster_scores)

    if dominant:
        conversation.dominant_cluster = dominant.value
        conversation.lead_data["detected_objection"] = analysis.detected_objection

    if not is_ambiguous and dominant:
        # Clear cluster -> move to confirmation
        return [UpdateStage(ConversationStage.CONFIRMING)]

    # Ambiguous -> hand off to Qualifier for Q1 clarification
    return await ask_q1(conversation, message_text)


def _lead_context_str(conversation: Conversation) -> str:
    data = conversation.lead_data
    parts = []
    for key in ("name", "role", "company", "origin", "email"):
        if data.get(key):
            parts.append(f"{key}: {data[key]}")
    return "\n".join(parts) if parts else "Sem dados previos."
