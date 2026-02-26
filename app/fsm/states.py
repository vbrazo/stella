from app.models.conversation import ConversationStage

# Define valid state transitions.
# Key = current state, Value = set of allowed next states.
TRANSITIONS: dict[ConversationStage, set[ConversationStage]] = {
    ConversationStage.IDLE: {
        ConversationStage.OPENING_SENT,
    },
    ConversationStage.OPENING_SENT: {
        ConversationStage.AWAITING_INTENT,
    },
    ConversationStage.AWAITING_INTENT: {
        ConversationStage.CONFIRMING,
        ConversationStage.ASKING_Q1,
        ConversationStage.PRICE_FALLBACK,
        ConversationStage.ESCALATED,
    },
    ConversationStage.PRICE_FALLBACK: {
        ConversationStage.AWAITING_INTENT,
        ConversationStage.ASKING_Q1,
        ConversationStage.ESCALATED,
    },
    ConversationStage.CONFIRMING: {
        ConversationStage.AWAITING_CONFIRMATION,
    },
    ConversationStage.AWAITING_CONFIRMATION: {
        ConversationStage.ASKING_Q1,
        ConversationStage.CONFIRMING,  # re-confirm if adjustment
        ConversationStage.ESCALATED,
    },
    ConversationStage.ASKING_Q1: {
        ConversationStage.AWAITING_Q1,
    },
    ConversationStage.AWAITING_Q1: {
        ConversationStage.ASKING_Q2,
        ConversationStage.ESCALATED,
    },
    ConversationStage.ASKING_Q2: {
        ConversationStage.AWAITING_Q2,
    },
    ConversationStage.AWAITING_Q2: {
        ConversationStage.ASKING_Q3,
        ConversationStage.RECOMMENDING,  # skip Q3 if enough info
        ConversationStage.ESCALATED,
    },
    ConversationStage.ASKING_Q3: {
        ConversationStage.AWAITING_Q3,
    },
    ConversationStage.AWAITING_Q3: {
        ConversationStage.RECOMMENDING,
        ConversationStage.ESCALATED,
    },
    ConversationStage.RECOMMENDING: {
        ConversationStage.CARD_SENT,
    },
    ConversationStage.CARD_SENT: {
        ConversationStage.AWAITING_DECISION,
    },
    ConversationStage.AWAITING_DECISION: {
        ConversationStage.HANDLING_OBJECTION,
        ConversationStage.COMPLETED,
        ConversationStage.ESCALATED,
    },
    ConversationStage.HANDLING_OBJECTION: {
        ConversationStage.CARD_SENT,  # alternative card
        ConversationStage.ESCALATED,
        ConversationStage.COMPLETED,
    },
    ConversationStage.ESCALATED: set(),  # terminal
    ConversationStage.COMPLETED: set(),  # terminal
}


def can_transition(current: ConversationStage, target: ConversationStage) -> bool:
    return target in TRANSITIONS.get(current, set())
