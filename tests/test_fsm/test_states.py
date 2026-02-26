from app.fsm.states import can_transition
from app.models.conversation import ConversationStage


def test_idle_to_opening():
    assert can_transition(ConversationStage.IDLE, ConversationStage.OPENING_SENT)


def test_idle_cannot_skip_to_card():
    assert not can_transition(ConversationStage.IDLE, ConversationStage.CARD_SENT)


def test_awaiting_intent_to_confirming():
    assert can_transition(ConversationStage.AWAITING_INTENT, ConversationStage.CONFIRMING)


def test_awaiting_intent_to_price_fallback():
    assert can_transition(ConversationStage.AWAITING_INTENT, ConversationStage.PRICE_FALLBACK)


def test_price_fallback_to_awaiting_intent():
    assert can_transition(ConversationStage.PRICE_FALLBACK, ConversationStage.AWAITING_INTENT)


def test_awaiting_confirmation_to_asking_q1():
    assert can_transition(ConversationStage.AWAITING_CONFIRMATION, ConversationStage.ASKING_Q1)


def test_full_happy_path():
    """Test full happy path transitions are all valid."""
    path = [
        ConversationStage.IDLE,
        ConversationStage.OPENING_SENT,
        ConversationStage.AWAITING_INTENT,
        ConversationStage.CONFIRMING,
        ConversationStage.AWAITING_CONFIRMATION,
        ConversationStage.ASKING_Q1,
        ConversationStage.AWAITING_Q1,
        ConversationStage.ASKING_Q2,
        ConversationStage.AWAITING_Q2,
        ConversationStage.ASKING_Q3,
        ConversationStage.AWAITING_Q3,
        ConversationStage.RECOMMENDING,
        ConversationStage.CARD_SENT,
        ConversationStage.AWAITING_DECISION,
        ConversationStage.COMPLETED,
    ]
    for i in range(len(path) - 1):
        assert can_transition(path[i], path[i + 1]), f"Failed: {path[i]} -> {path[i+1]}"


def test_escalated_is_terminal():
    """Escalated state has no valid transitions."""
    for stage in ConversationStage:
        if stage != ConversationStage.ESCALATED:
            assert not can_transition(ConversationStage.ESCALATED, stage)


def test_completed_is_terminal():
    """Completed state has no valid transitions."""
    for stage in ConversationStage:
        if stage != ConversationStage.COMPLETED:
            assert not can_transition(ConversationStage.COMPLETED, stage)


def test_card_sent_to_objection():
    assert can_transition(ConversationStage.AWAITING_DECISION, ConversationStage.HANDLING_OBJECTION)


def test_objection_to_alternative_card():
    assert can_transition(ConversationStage.HANDLING_OBJECTION, ConversationStage.CARD_SENT)
