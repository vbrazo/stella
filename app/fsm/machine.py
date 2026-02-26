import logging
from dataclasses import dataclass

from app.fsm.states import can_transition
from app.integrations.whatsapp.models import InteractiveButton, InteractiveCard
from app.models.conversation import Conversation, ConversationStage

logger = logging.getLogger(__name__)


# --- Actions ---


@dataclass
class SendText:
    text: str


@dataclass
class SendButtons:
    body: str
    buttons: list[InteractiveButton]


@dataclass
class SendCard:
    card: InteractiveCard


@dataclass
class UpdateStage:
    stage: ConversationStage


@dataclass
class Escalate:
    reason: str


@dataclass
class LogCRM:
    data: dict


Action = SendText | SendButtons | SendCard | UpdateStage | Escalate | LogCRM


# --- State Machine ---


class StateMachine:
    def __init__(self):
        from app.fsm.handlers import (
            closing,
            confirmation,
            intent,
            objection,
            opening,
            price_fallback,
            recommendation,
        )

        self._handlers: dict[ConversationStage, object] = {
            ConversationStage.IDLE: opening,
            ConversationStage.OPENING_SENT: opening,
            ConversationStage.AWAITING_INTENT: intent,
            ConversationStage.PRICE_FALLBACK: price_fallback,
            ConversationStage.CONFIRMING: confirmation,
            ConversationStage.AWAITING_CONFIRMATION: confirmation,
            ConversationStage.ASKING_Q1: intent,
            ConversationStage.AWAITING_Q1: intent,
            ConversationStage.ASKING_Q2: intent,
            ConversationStage.AWAITING_Q2: intent,
            ConversationStage.ASKING_Q3: intent,
            ConversationStage.AWAITING_Q3: intent,
            ConversationStage.RECOMMENDING: recommendation,
            ConversationStage.CARD_SENT: closing,
            ConversationStage.AWAITING_DECISION: closing,
            ConversationStage.HANDLING_OBJECTION: objection,
        }

    async def process(self, conversation: Conversation, message_text: str) -> list[Action]:
        """Process an incoming message and return a list of actions to execute."""
        stage = conversation.stage
        handler = self._handlers.get(stage)

        if handler is None:
            logger.warning("No handler for stage %s", stage)
            return []

        actions: list[Action] = await handler.handle(conversation, message_text)

        # Validate and apply stage transitions
        validated: list[Action] = []
        for action in actions:
            if isinstance(action, UpdateStage):
                if can_transition(conversation.stage, action.stage):
                    conversation.stage = action.stage
                    validated.append(action)
                else:
                    logger.error(
                        "Invalid transition %s -> %s",
                        conversation.stage,
                        action.stage,
                    )
            else:
                validated.append(action)

        return validated
