"""Agent 3 (Closer): Post-card closing and decision processing.

Sends closing message after card, then processes the lead's decision:
- Purchase signals -> complete
- Objection signals -> hand to objection handler
- Quick questions -> answer inline and stay in decision stage
"""

import logging

from app.fsm.machine import Action, SendText, UpdateStage
from app.llm import get_llm
from app.llm.prompts.closer import CLOSING_SYSTEM, QUICK_QUESTION_SYSTEM
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)

# Signals that lead wants to proceed with purchase
PURCHASE_SIGNALS = [
    "garantir",
    "comprar",
    "quero",
    "vou fazer",
    "inscrever",
    "fechar",
    "vou garantir",
    "bora",
    "vamos",
    "site",
]

# Signals that lead has an objection
OBJECTION_SIGNALS = [
    "caro",
    "preco",
    "pensar",
    "depois",
    "nao sei",
    "duvida",
    "orcamento",
    "empresa",
    "agenda",
    "tempo",
    "avaliar",
]


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    stage = conversation.stage

    if stage == ConversationStage.CARD_SENT:
        return await _send_closing(conversation)

    if stage == ConversationStage.AWAITING_DECISION:
        return await _process_decision(conversation, message_text)

    return []


async def _send_closing(conversation: Conversation) -> list[Action]:
    """Send closing message after card."""
    llm = get_llm()
    history = _conversation_history(conversation)

    closing_msg = await llm.complete_text(
        system=CLOSING_SYSTEM.format(conversation_history=history),
        messages=[{"role": "user", "content": "Gere a mensagem de proximo passo."}],
        temperature=0.7,
    )

    return [
        SendText(closing_msg.strip()),
        UpdateStage(ConversationStage.AWAITING_DECISION),
    ]


async def _process_decision(conversation: Conversation, message_text: str) -> list[Action]:
    """Process lead's decision after card + closing."""
    text = message_text.strip().lower()

    # Check for purchase intent
    if any(s in text for s in PURCHASE_SIGNALS):
        return [
            SendText("Perfeito! Voce consegue garantir sua vaga direto pelo botao do card que enviei."),
            UpdateStage(ConversationStage.COMPLETED),
        ]

    # Check for objection
    if any(s in text for s in OBJECTION_SIGNALS):
        return [UpdateStage(ConversationStage.HANDLING_OBJECTION)]

    # Quick question -- answer and stay in decision stage
    llm = get_llm()
    history = _conversation_history(conversation)

    answer = await llm.complete_text(
        system=QUICK_QUESTION_SYSTEM.format(
            product_recommended=conversation.product_recommended or "",
            conversation_history=history,
        ),
        messages=[{"role": "user", "content": message_text}],
        temperature=0.7,
    )

    return [SendText(answer.strip())]


def _conversation_history(conversation: Conversation) -> str:
    lines = []
    for msg in conversation.messages[-10:]:
        prefix = "Lead" if msg.direction == "inbound" else "Stella"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines)
