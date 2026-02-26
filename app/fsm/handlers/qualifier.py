"""Agent 2 (Qualifier): Structured qualification questions Q1-Q3.

Gathers lead profile data through 3 contextual questions:
- Q1: Strategic moment (cluster confirmation)
- Q2: Primary objection (what blocks them)
- Q3: LinkedIn URL (for enrichment)

Hands off to Agent 3 (Closer) at RECOMMENDING stage.
"""

import logging

from app.engine.classifier import map_objection
from app.fsm.machine import Action, SendButtons, SendText, UpdateStage
from app.integrations.whatsapp.models import InteractiveButton
from app.llm import get_llm
from app.llm.prompts.concierge import MICRO_VALIDATION_SYSTEM
from app.llm.prompts.qualifier import Q1_SYSTEM, Q2_SYSTEM, Q3_SYSTEM
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)

# Button options for Q1
Q1_BUTTONS = [
    InteractiveButton(id="q1_evolution", title="Jornada de 12 meses"),
    InteractiveButton(id="q1_challenge", title="Desafio especifico"),
    InteractiveButton(id="q1_flexibility", title="No meu ritmo"),
]

# Button options for Q2
Q2_BUTTONS = [
    InteractiveButton(id="q2_budget", title="Orcamento limitado"),
    InteractiveButton(id="q2_corporate", title="Dependo da empresa"),
    InteractiveButton(id="q2_schedule", title="Agenda no limite"),
]

# Q1 answer mapping
Q1_MAP = {
    "q1_evolution": "structured_evolution",
    "q1_challenge": "specific_challenge",
    "q1_flexibility": "flexibility_needed",
    "q1_meeting": "strategic_evaluation",
}

# Q2 answer mapping
Q2_MAP = {
    "q2_budget": "financial_personal",
    "q2_corporate": "corporate_dependency",
    "q2_schedule": "schedule_limitation",
    "q2_smaller": "start_smaller",
    "q2_unsure": "lack_of_conviction",
}


async def handle(conversation: Conversation, message_text: str) -> list[Action]:
    stage = conversation.stage

    if stage == ConversationStage.ASKING_Q1:
        return [UpdateStage(ConversationStage.AWAITING_Q1)]

    if stage == ConversationStage.AWAITING_Q1:
        return await _process_q1(conversation, message_text)

    if stage == ConversationStage.ASKING_Q2:
        return [UpdateStage(ConversationStage.AWAITING_Q2)]

    if stage == ConversationStage.AWAITING_Q2:
        return await _process_q2(conversation, message_text)

    if stage == ConversationStage.ASKING_Q3:
        return [UpdateStage(ConversationStage.AWAITING_Q3)]

    if stage == ConversationStage.AWAITING_Q3:
        return await _process_q3(conversation, message_text)

    return []


async def ask_q1(conversation: Conversation, message_text: str) -> list[Action]:
    """Ask structured question 1 (momento estrategico). Called from intent handler on ambiguous cluster."""
    llm = get_llm()
    actions: list[Action] = []

    # Generate micro-validation
    micro = await _generate_micro_validation(llm, message_text)
    if micro:
        actions.append(SendText(micro))

    history = _conversation_history(conversation)
    q1_text = await llm.complete_text(
        system=Q1_SYSTEM.format(micro_validation=micro or "", conversation_history=history),
        messages=[{"role": "user", "content": "Gere a pergunta Q1."}],
        temperature=0.7,
    )

    actions.append(SendButtons(body=q1_text.strip(), buttons=Q1_BUTTONS))
    conversation.structured_question_count += 1
    actions.append(UpdateStage(ConversationStage.ASKING_Q1))
    return actions


async def _process_q1(conversation: Conversation, message_text: str) -> list[Action]:
    """Process Q1 answer and ask Q2."""
    # Map button reply or free text
    mapped = Q1_MAP.get(message_text, message_text)
    conversation.q1_answer = mapped

    # Update cluster based on Q1
    if mapped in ("structured_evolution", "specific_challenge", "flexibility_needed", "strategic_evaluation"):
        conversation.dominant_cluster = mapped

    return await _ask_q2(conversation, message_text)


async def _ask_q2(conversation: Conversation, message_text: str) -> list[Action]:
    """Ask structured question 2 (objecao principal)."""
    llm = get_llm()
    actions: list[Action] = []

    micro = await _generate_micro_validation(llm, message_text)
    if micro:
        actions.append(SendText(micro))

    history = _conversation_history(conversation)
    q2_text = await llm.complete_text(
        system=Q2_SYSTEM.format(
            micro_validation=micro or "",
            q1_answer=conversation.q1_answer or "",
            conversation_history=history,
        ),
        messages=[{"role": "user", "content": "Gere a pergunta Q2."}],
        temperature=0.7,
    )

    actions.append(SendButtons(body=q2_text.strip(), buttons=Q2_BUTTONS))
    conversation.structured_question_count += 1
    actions.append(UpdateStage(ConversationStage.ASKING_Q2))
    return actions


async def _process_q2(conversation: Conversation, message_text: str) -> list[Action]:
    """Process Q2 answer and ask Q3."""
    mapped = Q2_MAP.get(message_text, message_text)
    conversation.q2_answer = mapped
    conversation.lead_data["declared_objection"] = mapped

    # Update lead objection
    objection = map_objection(mapped)
    conversation.lead_data["objection"] = objection.value

    # If we already have LinkedIn, skip Q3 -> recommend
    if conversation.lead_data.get("linkedin_url"):
        return [UpdateStage(ConversationStage.RECOMMENDING)]

    return await _ask_q3(conversation, message_text)


async def _ask_q3(conversation: Conversation, message_text: str) -> list[Action]:
    """Ask structured question 3 (LinkedIn)."""
    llm = get_llm()
    actions: list[Action] = []

    micro = await _generate_micro_validation(llm, message_text)
    if micro:
        actions.append(SendText(micro))

    history = _conversation_history(conversation)
    q3_text = await llm.complete_text(
        system=Q3_SYSTEM.format(micro_validation=micro or "", conversation_history=history),
        messages=[{"role": "user", "content": "Gere a pergunta Q3."}],
        temperature=0.7,
    )

    actions.append(SendText(q3_text.strip()))
    conversation.structured_question_count += 1
    actions.append(UpdateStage(ConversationStage.ASKING_Q3))
    return actions


async def _process_q3(conversation: Conversation, message_text: str) -> list[Action]:
    """Process Q3 answer (LinkedIn URL or decline) and hand off to Closer."""
    text = message_text.strip()

    # Check if it looks like a LinkedIn URL
    if "linkedin.com" in text.lower():
        conversation.lead_data["linkedin_url"] = text

    return [UpdateStage(ConversationStage.RECOMMENDING)]


async def _generate_micro_validation(llm, lead_response: str) -> str | None:
    """Generate a short contextual micro-validation."""
    try:
        micro = await llm.complete_text(
            system=MICRO_VALIDATION_SYSTEM.format(lead_response=lead_response),
            messages=[{"role": "user", "content": lead_response}],
            temperature=0.8,
        )
        result = micro.strip()
        return result if len(result) <= 60 else result[:57] + "..."
    except Exception:
        logger.exception("Failed to generate micro-validation")
        return None


def _conversation_history(conversation: Conversation) -> str:
    lines = []
    for msg in conversation.messages[-10:]:
        prefix = "Lead" if msg.direction == "inbound" else "Stella"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines) if lines else "Inicio da conversa."
