"""Agent 2: Closing / next step handler."""

import logging

from app.fsm.machine import Action, SendText, UpdateStage
from app.llm import get_llm
from app.llm.prompts.qualifier import CLOSING_SYSTEM
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
    "preço",
    "pensar",
    "depois",
    "não sei",
    "dúvida",
    "orçamento",
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
        messages=[{"role": "user", "content": "Gere a mensagem de próximo passo."}],
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
            SendText("Perfeito! Você consegue garantir sua vaga direto pelo botão do card que enviei."),
            UpdateStage(ConversationStage.COMPLETED),
        ]

    # Check for objection
    if any(s in text for s in OBJECTION_SIGNALS):
        return [UpdateStage(ConversationStage.HANDLING_OBJECTION)]

    # Quick question — answer and stay in decision stage
    llm = get_llm()
    history = _conversation_history(conversation)

    answer = await llm.complete_text(
        system=(
            "Você é a Stella, consultora de carreira da Strides. O lead fez uma pergunta rápida após receber "
            "a recomendação. Responda de forma curta (max 140 chars), consultiva, e termine conduzindo para decisão.\n\n"
            f"Produto recomendado: {conversation.product_recommended}\n"
            f"Contexto:\n{history}"
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
