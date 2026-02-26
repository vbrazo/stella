"""Escalation handler — hand off to human."""

import logging

from app.fsm.machine import Action, LogCRM, SendText, UpdateStage
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)

ESCALATION_MESSAGE = (
    "Posso te colocar para conversar com alguém do nosso time "
    "para um diagnóstico estratégico do seu momento. É uma conversa "
    "objetiva de 30 min para te indicar a melhor porta de entrada "
    "para a Strides. Faz sentido para você?"
)

HUMAN_HANDOFF_MESSAGE = (
    "Oi, aqui é a Stella da Strides. Acabo de ler o contexto "
    "da sua conversa conosco até aqui. Em que posso te ajudar exatamente?"
)


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    """Handle escalation to human."""
    actions: list[Action] = []

    if not conversation.escalated:
        # First escalation: offer diagnostic meeting
        conversation.escalated = True
        actions.append(SendText(ESCALATION_MESSAGE))

        # Log escalation to CRM
        actions.append(LogCRM({
            "event": "escalation",
            "reason": conversation.escalation_reason or "unspecified",
            "cluster": conversation.dominant_cluster,
            "product_recommended": conversation.product_recommended,
            "phone": conversation.phone,
        }))

        actions.append(UpdateStage(ConversationStage.ESCALATED))
    else:
        # Already escalated — if human hasn't responded within timeout,
        # Stella takes over with human persona
        actions.append(SendText(HUMAN_HANDOFF_MESSAGE))

    return actions
