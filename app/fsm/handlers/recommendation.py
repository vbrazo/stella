"""Agent 2: Product recommendation and card sending handler."""

import logging

from app.engine.cards import build_card
from app.engine.classifier import ClusterScores
from app.engine.recommender import recommend
from app.fsm.machine import Action, LogCRM, SendCard, SendText, UpdateStage
from app.llm import get_llm
from app.llm.prompts.concierge import RECOMMENDATION_MESSAGE_SYSTEM
from app.models.conversation import Conversation, ConversationStage
from app.models.lead import Lead, LeadCluster, LeadObjection
from app.models.recommendation import CARD_TEMPLATES

logger = logging.getLogger(__name__)


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    if conversation.stage != ConversationStage.RECOMMENDING:
        return []

    return await _recommend_and_send_card(conversation)


async def _recommend_and_send_card(conversation: Conversation) -> list[Action]:
    """Run recommender, generate message, send card."""
    actions: list[Action] = []

    # Build lead model from conversation data
    lead = _build_lead(conversation)

    # Build cluster scores
    scores = ClusterScores(**conversation.cluster_scores) if conversation.cluster_scores else ClusterScores(
        structured_evolution=0.3,
        specific_challenge=0.5,
        flexibility_needed=0.1,
        strategic_evaluation=0.1,
    )

    # Get recommendation
    rec = recommend(lead, scores)
    logger.info(
        "Recommendation for %s: primary=%s, alt=%s, reason=%s",
        conversation.phone,
        rec.primary,
        rec.alternative,
        rec.reasoning,
    )

    # Store in conversation
    conversation.product_recommended = rec.primary.value
    conversation.product_alternative = rec.alternative.value if rec.alternative else None

    # Generate personalized recommendation message
    llm = get_llm()
    history = _conversation_history(conversation)

    primary_template = CARD_TEMPLATES.get(rec.primary)
    alt_template = CARD_TEMPLATES.get(rec.alternative) if rec.alternative else None

    rec_msg = await llm.complete_text(
        system=RECOMMENDATION_MESSAGE_SYSTEM.format(
            primary_product=primary_template.title if primary_template else rec.primary.value,
            alternative_product=alt_template.title if alt_template else "nenhuma",
            reasoning=rec.reasoning,
            conversation_history=history,
        ),
        messages=[{"role": "user", "content": "Gere a mensagem de recomendação."}],
        temperature=0.7,
    )

    # Send recommendation text (split into WhatsApp-style messages)
    for line in rec_msg.strip().split("\n"):
        line = line.strip()
        if line:
            actions.append(SendText(line))

    # Send the card for the primary product
    card = build_card(rec.primary)
    actions.append(SendCard(card))
    conversation.card_sent = True

    # Log to CRM
    actions.append(LogCRM({
        "event": "recommendation_sent",
        "product_primary": rec.primary.value,
        "product_alternative": rec.alternative.value if rec.alternative else None,
        "cluster": conversation.dominant_cluster,
        "reasoning": rec.reasoning,
    }))

    actions.append(UpdateStage(ConversationStage.CARD_SENT))
    return actions


def _build_lead(conversation: Conversation) -> Lead:
    """Build a Lead model from conversation data."""
    data = conversation.lead_data
    objection_str = data.get("objection", data.get("declared_objection", "none"))

    # Map Q1 answer to cluster
    cluster = None
    if conversation.dominant_cluster:
        try:
            cluster = LeadCluster(conversation.dominant_cluster)
        except ValueError:
            pass

    # Map Q2 answer to objection
    objection = LeadObjection.NONE
    try:
        objection = LeadObjection(objection_str)
    except ValueError:
        pass

    # Determine financial/live availability from objection
    has_financial = objection not in (LeadObjection.FINANCIAL_PERSONAL, LeadObjection.START_SMALLER)
    has_live = objection != LeadObjection.SCHEDULE_LIMITATION

    return Lead(
        phone=conversation.phone,
        name=data.get("name"),
        email=data.get("email"),
        linkedin_url=data.get("linkedin_url"),
        role=data.get("role"),
        company=data.get("company"),
        seniority=data.get("seniority"),
        qualification_scores=data.get("qualification_scores", []),
        cluster=cluster,
        objection=objection,
        has_financial_availability=has_financial,
        has_live_availability=has_live,
        ai_interest=data.get("ai_interest", False),
    )


def _conversation_history(conversation: Conversation) -> str:
    lines = []
    for msg in conversation.messages[-10:]:
        prefix = "Lead" if msg.direction == "inbound" else "Stella"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines) if lines else "Início da conversa."
