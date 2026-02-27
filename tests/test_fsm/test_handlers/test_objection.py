"""Tests for objection handler logic."""

from unittest.mock import patch

import pytest

from app.fsm.handlers import objection
from app.fsm.machine import Escalate, SendCard, SendText, UpdateStage
from app.models.conversation import ConversationStage


@pytest.mark.asyncio
async def test_financial_objection_with_alternative_sends_alt_card(conversation, fake_llm):
    """Financial objection + alternative product -> sends alternative card + CARD_SENT."""
    conversation.stage = ConversationStage.HANDLING_OBJECTION
    conversation.product_recommended = "programa_head_tech"
    conversation.product_alternative = "trilhas"
    fake_llm.text_responses = ["Entendo a preocupacao com investimento.\nTemos uma opcao mais acessivel."]

    with patch("app.fsm.handlers.objection.get_llm", return_value=fake_llm):
        actions = await objection.handle(conversation, "achei caro demais")

    assert any(isinstance(a, SendText) for a in actions)
    assert any(isinstance(a, SendCard) for a in actions)
    stage_actions = [a for a in actions if isinstance(a, UpdateStage)]
    assert any(a.stage == ConversationStage.CARD_SENT for a in stage_actions)
    assert conversation.lead_data.get("alternative_card_sent") is True


@pytest.mark.asyncio
async def test_lack_of_conviction_without_alt_escalates(conversation, fake_llm):
    """Conviction objection + no alternative + already sent alt -> ESCALATED."""
    conversation.stage = ConversationStage.HANDLING_OBJECTION
    conversation.product_recommended = "programa_head_tech"
    conversation.product_alternative = None
    conversation.lead_data["alternative_card_sent"] = True
    fake_llm.text_responses = ["Entendo que precisa pensar."]

    with patch("app.fsm.handlers.objection.get_llm", return_value=fake_llm):
        actions = await objection.handle(conversation, "preciso pensar mais")

    assert any(isinstance(a, Escalate) for a in actions)
    stage_actions = [a for a in actions if isinstance(a, UpdateStage)]
    assert any(a.stage == ConversationStage.ESCALATED for a in stage_actions)


@pytest.mark.asyncio
async def test_non_conviction_without_alt_completes(conversation, fake_llm):
    """Non-conviction objection + no alternative -> COMPLETED (graceful close)."""
    conversation.stage = ConversationStage.HANDLING_OBJECTION
    conversation.product_recommended = "programa_head_tech"
    conversation.product_alternative = None
    conversation.lead_data["alternative_card_sent"] = True
    fake_llm.text_responses = ["Entendo a questao de agenda."]

    with patch("app.fsm.handlers.objection.get_llm", return_value=fake_llm):
        actions = await objection.handle(conversation, "nao tenho tempo na agenda")

    stage_actions = [a for a in actions if isinstance(a, UpdateStage)]
    assert any(a.stage == ConversationStage.COMPLETED for a in stage_actions)
    assert not any(isinstance(a, Escalate) for a in actions)


@pytest.mark.asyncio
async def test_non_handling_stage_returns_empty(conversation):
    """Handler returns empty when not in HANDLING_OBJECTION stage."""
    conversation.stage = ConversationStage.AWAITING_DECISION
    actions = await objection.handle(conversation, "achei caro")
    assert actions == []
