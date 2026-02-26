"""Agent 2: Smart confirmation handler."""

import logging

from app.fsm.machine import Action, SendText, UpdateStage
from app.llm import get_llm
from app.llm.prompts.concierge import CONFIRMATION_SYSTEM
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)

# Positive confirmation patterns (Portuguese)
POSITIVE_PATTERNS = [
    "sim",
    "isso",
    "exato",
    "faz sentido",
    "isso mesmo",
    "exatamente",
    "é isso",
    "correto",
    "perfeito",
    "com certeza",
    "isso aí",
    "bora",
    "vamos",
    "pode ser",
    "beleza",
]


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    stage = conversation.stage

    if stage == ConversationStage.CONFIRMING:
        return await _send_confirmation(conversation)

    if stage == ConversationStage.AWAITING_CONFIRMATION:
        return await _process_confirmation(conversation, message_text)

    return []


async def _send_confirmation(conversation: Conversation) -> list[Action]:
    """Generate and send confirmation message."""
    llm = get_llm()
    history = _conversation_history(conversation)
    cluster = conversation.dominant_cluster or "specific_challenge"

    confirmation_msg = await llm.complete_text(
        system=CONFIRMATION_SYSTEM.format(
            dominant_cluster=cluster,
            conversation_history=history,
        ),
        messages=[{"role": "user", "content": "Gere a confirmação."}],
        temperature=0.7,
    )

    actions: list[Action] = []

    # Split into multiple messages if separated by \n
    for line in confirmation_msg.strip().split("\n"):
        line = line.strip()
        if line:
            actions.append(SendText(line))

    actions.append(UpdateStage(ConversationStage.AWAITING_CONFIRMATION))
    return actions


async def _process_confirmation(conversation: Conversation, message_text: str) -> list[Action]:
    """Process lead's response to confirmation."""
    text = message_text.strip().lower()

    # Check if positive confirmation
    is_positive = any(pattern in text for pattern in POSITIVE_PATTERNS)

    if is_positive:
        # Confirmed → move to structured questions
        return [UpdateStage(ConversationStage.ASKING_Q1)]

    # Lead is adjusting — re-run confirmation with new context
    # The lead's adjustment becomes part of the conversation history
    return [UpdateStage(ConversationStage.CONFIRMING)]


def _conversation_history(conversation: Conversation) -> str:
    lines = []
    for msg in conversation.messages[-10:]:
        prefix = "Lead" if msg.direction == "inbound" else "Stella"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines) if lines else "Início da conversa."
