"""Tests for intent handler routing."""

from unittest.mock import AsyncMock, patch

import pytest

from app.engine.classifier import ClusterScores, IntentAnalysis
from app.fsm.handlers import intent
from app.fsm.machine import SendButtons, UpdateStage
from app.models.conversation import Conversation, ConversationStage


@pytest.mark.asyncio
async def test_clear_cluster_goes_to_confirming(conversation, fake_llm):
    """High-confidence classification routes to CONFIRMING."""
    conversation.stage = ConversationStage.AWAITING_INTENT
    fake_llm.json_responses = [
        IntentAnalysis(
            cluster_scores=ClusterScores(
                structured_evolution=0.85,
                specific_challenge=0.2,
                flexibility_needed=0.1,
                strategic_evaluation=0.1,
            ),
        )
    ]

    with patch("app.fsm.handlers.intent.get_llm", return_value=fake_llm):
        actions = await intent.handle(conversation, "quero evoluir na lideranca")

    stage_actions = [a for a in actions if isinstance(a, UpdateStage)]
    assert any(a.stage == ConversationStage.CONFIRMING for a in stage_actions)


@pytest.mark.asyncio
async def test_ambiguous_cluster_goes_to_asking_q1(conversation, fake_llm):
    """Ambiguous classification routes to qualifier (ASKING_Q1)."""
    conversation.stage = ConversationStage.AWAITING_INTENT
    fake_llm.json_responses = [
        IntentAnalysis(
            cluster_scores=ClusterScores(
                structured_evolution=0.4,
                specific_challenge=0.35,
                flexibility_needed=0.3,
                strategic_evaluation=0.2,
            ),
        )
    ]
    # ask_q1 calls complete_text for micro-validation and Q1 text
    fake_llm.text_responses = ["Entendi!", "Qual seu momento?"]

    with patch("app.fsm.handlers.intent.get_llm", return_value=fake_llm), \
         patch("app.fsm.handlers.qualifier.get_llm", return_value=fake_llm):
        actions = await intent.handle(conversation, "quero saber mais")

    stage_actions = [a for a in actions if isinstance(a, UpdateStage)]
    assert any(a.stage == ConversationStage.ASKING_Q1 for a in stage_actions)
    # Should include SendButtons for Q1
    assert any(isinstance(a, SendButtons) for a in actions)


@pytest.mark.asyncio
async def test_price_request_goes_to_price_fallback(conversation, fake_llm):
    """price_request=True routes to PRICE_FALLBACK."""
    conversation.stage = ConversationStage.AWAITING_INTENT
    fake_llm.json_responses = [
        IntentAnalysis(
            cluster_scores=ClusterScores(
                structured_evolution=0.3,
                specific_challenge=0.3,
                flexibility_needed=0.3,
                strategic_evaluation=0.3,
            ),
            price_request=True,
        )
    ]

    with patch("app.fsm.handlers.intent.get_llm", return_value=fake_llm):
        actions = await intent.handle(conversation, "quanto custa?")

    stage_actions = [a for a in actions if isinstance(a, UpdateStage)]
    assert any(a.stage == ConversationStage.PRICE_FALLBACK for a in stage_actions)


@pytest.mark.asyncio
async def test_non_awaiting_intent_returns_empty(conversation):
    """Handler returns empty when stage is not AWAITING_INTENT."""
    conversation.stage = ConversationStage.IDLE
    actions = await intent.handle(conversation, "oi")
    assert actions == []
