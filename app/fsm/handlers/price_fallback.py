"""Price fallback handler per Stella v2.0 spec."""

import logging

from app.fsm.machine import Action, SendText, UpdateStage
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)

# Multi-message price responses by insistence level
PRICE_RESPONSE_L1 = [
    "Os programas da Strides variam hoje entre R$ 1.000 e R$ 17.000, dependendo da trilha e da profundidade da jornada.",
    "Essa diferença existe porque cada profissional está em um momento diferente. Alguns querem evolução estruturada ao longo do ano. Outros têm um desafio específico.",
    "O investimento depende do seu momento atual e do tipo de transformação que você busca.",
    "Para te indicar o valor e a trilha certa, preciso entender alguns pontos sobre o seu momento. Posso te fazer perguntas rápidas?",
]

PRICE_RESPONSE_L2 = [
    "Entendo. Como temos programas com profundidades e formatos bem diferentes, um número isolado não faria sentido.",
    "Me conta rapidamente: qual é o principal desafio que você está enfrentando hoje?",
]

PRICE_RESPONSE_L3 = [
    "O menor investimento hoje é em torno de R$ 1.000 e o mais completo chega a R$ 17.000.",
    "A diferença está no nível de acompanhamento, profundidade e tempo de jornada.",
    "Pra te dizer onde você se encaixa: você tá buscando algo estruturado ao longo do ano ou resolver um desafio específico agora?",
]

PRICE_OBJECTION_RESPONSE = [
    "Pode ser que não faça sentido mesmo dependendo do momento.",
    "Por isso é importante entender o que você tá tentando resolver. Se for algo pontual, provavelmente temos um formato mais enxuto.",
]


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    """Handle price requests with multi-level responses."""
    actions: list[Action] = []

    conversation.price_ask_count += 1
    level = conversation.price_ask_count

    # Check if lead is saying it's expensive (not asking price)
    text = message_text.lower()
    if any(w in text for w in ("caro", "muito", "absurdo", "pesado")):
        for msg in PRICE_OBJECTION_RESPONSE:
            actions.append(SendText(msg))
        actions.append(UpdateStage(ConversationStage.AWAITING_INTENT))
        return actions

    if level == 1:
        for msg in PRICE_RESPONSE_L1:
            actions.append(SendText(msg))
    elif level == 2:
        for msg in PRICE_RESPONSE_L2:
            actions.append(SendText(msg))
    else:
        for msg in PRICE_RESPONSE_L3:
            actions.append(SendText(msg))

    # Return to intent extraction after price response
    actions.append(UpdateStage(ConversationStage.AWAITING_INTENT))
    return actions
