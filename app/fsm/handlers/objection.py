"""Agent 3 (Closer): Objection handling after card sent.

Detects objection type, generates contextual response via LLM,
and optionally sends an alternative product card.
"""

import logging

from app.engine.cards import build_card
from app.fsm.machine import Action, Escalate, SendCard, SendText, UpdateStage
from app.llm import get_llm
from app.llm.prompts.closer import OBJECTION_HANDLER_SYSTEM
from app.models.conversation import Conversation, ConversationStage
from app.models.lead import LeadObjection
from app.models.recommendation import Product

logger = logging.getLogger(__name__)


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    if conversation.stage != ConversationStage.HANDLING_OBJECTION:
        return []

    return await _handle_objection(conversation, message_text)


async def _handle_objection(conversation: Conversation, message_text: str) -> list[Action]:
    """Handle one objection. May send alternative card or escalate."""
    actions: list[Action] = []

    # Detect objection type from message
    objection_type = _detect_objection(message_text)

    # If we have an alternative product and haven't sent it yet, offer it
    alternative = conversation.product_alternative
    has_alternative = alternative and not conversation.lead_data.get("alternative_card_sent")

    llm = get_llm()
    history = _conversation_history(conversation)

    # Generate objection response
    obj_msg = await llm.complete_text(
        system=OBJECTION_HANDLER_SYSTEM.format(
            objection_type=objection_type.value,
            product_recommended=conversation.product_recommended or "",
            alternative_product=alternative or "nenhuma",
            conversation_history=history,
        ),
        messages=[{"role": "user", "content": message_text}],
        temperature=0.7,
    )

    for line in obj_msg.strip().split("\n"):
        line = line.strip()
        if line:
            actions.append(SendText(line))

    if has_alternative:
        # Send alternative card
        try:
            product = Product(alternative)
            card = build_card(product)
            actions.append(SendCard(card))
            conversation.lead_data["alternative_card_sent"] = True
            actions.append(UpdateStage(ConversationStage.CARD_SENT))
        except (ValueError, KeyError):
            logger.error("Invalid alternative product: %s", alternative)
            actions.append(UpdateStage(ConversationStage.ESCALATED))
    else:
        # No alternative left -- escalate if persistent
        if objection_type == LeadObjection.LACK_OF_CONVICTION:
            actions.append(Escalate("Indecisao persistente apos objecao"))
            actions.append(UpdateStage(ConversationStage.ESCALATED))
        else:
            # Close conversation gracefully
            actions.append(UpdateStage(ConversationStage.COMPLETED))

    return actions


def _detect_objection(message_text: str) -> LeadObjection:
    """Simple keyword-based objection detection."""
    text = message_text.lower()

    financial_signals = ["caro", "preco", "valor", "investimento", "grana", "orcamento", "dinheiro", "custo"]
    schedule_signals = ["agenda", "tempo", "horario", "nao consigo", "ocupado"]
    corporate_signals = ["empresa", "corporativo", "aprovacao", "patrocinio", "budget"]
    smaller_signals = ["menor", "mais simples", "comecar", "testar", "experimentar"]
    conviction_signals = ["pensar", "avaliar", "depois", "nao sei", "talvez", "duvida"]

    if any(s in text for s in financial_signals):
        return LeadObjection.FINANCIAL_PERSONAL
    if any(s in text for s in corporate_signals):
        return LeadObjection.CORPORATE_DEPENDENCY
    if any(s in text for s in schedule_signals):
        return LeadObjection.SCHEDULE_LIMITATION
    if any(s in text for s in smaller_signals):
        return LeadObjection.START_SMALLER
    if any(s in text for s in conviction_signals):
        return LeadObjection.LACK_OF_CONVICTION

    return LeadObjection.NONE


def _conversation_history(conversation: Conversation) -> str:
    lines = []
    for msg in conversation.messages[-10:]:
        prefix = "Lead" if msg.direction == "inbound" else "Stella"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines)
