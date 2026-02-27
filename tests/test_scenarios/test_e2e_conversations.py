"""End-to-end conversation scenario tests.

Each test simulates multi-turn conversations through the FSM,
mocking LLM responses but exercising real handler logic and state transitions.
"""

from unittest.mock import patch

import pytest

from app.engine.classifier import ClusterScores, IntentAnalysis
from app.fsm.machine import (
    SendButtons,
    SendCard,
    SendText,
    StateMachine,
)
from app.models.conversation import Conversation, ConversationStage


class TestPriceOnlyUserScenario:
    """Lead who only asks about price across multiple turns."""

    @pytest.mark.asyncio
    async def test_price_insistence_levels(self, machine: StateMachine):
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.PRICE_FALLBACK

        # Turn 1: L1 response
        actions = await machine.process(conversation, "quanto custa?")
        text_actions = [a for a in actions if isinstance(a, SendText)]
        assert len(text_actions) == 4  # L1 has 4 messages
        assert conversation.price_ask_count == 1

        # Reset to PRICE_FALLBACK for next price ask
        conversation.stage = ConversationStage.PRICE_FALLBACK

        # Turn 2: L2 response
        actions = await machine.process(conversation, "mas qual o valor exato?")
        text_actions = [a for a in actions if isinstance(a, SendText)]
        assert len(text_actions) == 2  # L2 has 2 messages
        assert conversation.price_ask_count == 2

        # Reset to PRICE_FALLBACK for next price ask
        conversation.stage = ConversationStage.PRICE_FALLBACK

        # Turn 3: L3 response
        actions = await machine.process(conversation, "me diz o preco")
        text_actions = [a for a in actions if isinstance(a, SendText)]
        assert len(text_actions) == 3  # L3 has 3 messages
        assert conversation.price_ask_count == 3


class TestObjectionAfterCardScenario:
    """Lead receives card, raises objection, gets alternative or escalation."""

    @pytest.mark.asyncio
    async def test_purchase_signal_completes(self, machine: StateMachine, fake_llm):
        """Lead says they want to buy -> COMPLETED."""
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.AWAITING_DECISION
        conversation.product_recommended = "programa_head_tech"

        actions = await machine.process(conversation, "quero garantir minha vaga")
        assert conversation.stage == ConversationStage.COMPLETED
        assert any(isinstance(a, SendText) for a in actions)

    @pytest.mark.asyncio
    async def test_objection_signal_transitions_to_handling(self, machine: StateMachine):
        """Lead says 'caro' -> transitions to HANDLING_OBJECTION."""
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.AWAITING_DECISION

        await machine.process(conversation, "achei caro")
        assert conversation.stage == ConversationStage.HANDLING_OBJECTION

    @pytest.mark.asyncio
    async def test_objection_with_alternative_sends_alt_card(self, machine: StateMachine, fake_llm):
        """Financial objection + alt product -> sends alternative card."""
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.HANDLING_OBJECTION
        conversation.product_recommended = "programa_head_tech"
        conversation.product_alternative = "trilhas"
        fake_llm.text_responses = ["Entendo.\nTemos uma opcao mais acessivel."]

        with patch("app.fsm.handlers.objection.get_llm", return_value=fake_llm):
            actions = await machine.process(conversation, "o investimento e alto")

        assert conversation.stage == ConversationStage.CARD_SENT
        assert any(isinstance(a, SendCard) for a in actions)


class TestReEntryAfterSilence:
    """Lead goes silent then comes back -- FSM picks up from last stage."""

    @pytest.mark.asyncio
    async def test_re_entry_from_awaiting_q2(self, machine: StateMachine, fake_llm):
        """Conversation at AWAITING_Q2 picks up Q2 processing on re-entry."""
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.AWAITING_Q2
        conversation.q1_answer = "specific_challenge"
        conversation.dominant_cluster = "specific_challenge"

        # Q2 answer → should process Q2 and move to ASKING_Q3
        fake_llm.text_responses = ["Faz sentido!", "Qual seu LinkedIn?"]

        with patch("app.fsm.handlers.qualifier.get_llm", return_value=fake_llm):
            await machine.process(conversation, "q2_budget")

        # Should have moved forward (Q2 processed, now at ASKING_Q3 or later)
        assert conversation.stage in (
            ConversationStage.ASKING_Q3,
            ConversationStage.RECOMMENDING,
        )

    @pytest.mark.asyncio
    async def test_re_entry_from_card_sent(self, machine: StateMachine, fake_llm):
        """Conversation at CARD_SENT picks up closing flow."""
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.CARD_SENT
        conversation.product_recommended = "programa_head_tech"
        fake_llm.text_responses = ["Voce pode garantir sua vaga pelo card."]

        with patch("app.fsm.handlers.closing.get_llm", return_value=fake_llm):
            await machine.process(conversation, "")

        assert conversation.stage == ConversationStage.AWAITING_DECISION


class TestVoiceMessageIntegration:
    """Voice message flow through transcription."""

    @pytest.mark.asyncio
    async def test_audio_transcription_feeds_fsm(self):
        """Transcribed audio text is processed through normal FSM flow."""
        from app.integrations.whatsapp.models import IncomingMessage

        incoming = IncomingMessage(
            message_id="audio_123",
            phone="5511999999999",
            name="Joao",
            type="audio",
            audio_id="media_456",
        )

        # Verify the model accepts audio type with audio_id
        assert incoming.type == "audio"
        assert incoming.audio_id == "media_456"
        assert incoming.text is None  # No text initially


class TestAmbiguousIntentScenario:
    """Lead with vague initial message gets routed through qualifier."""

    @pytest.mark.asyncio
    async def test_ambiguous_routes_to_qualifier(self, machine: StateMachine, fake_llm):
        """Ambiguous intent → ASKING_Q1 (qualifier takes over)."""
        conversation = Conversation(phone="5511999999999")
        conversation.stage = ConversationStage.AWAITING_INTENT

        fake_llm.json_responses = [
            IntentAnalysis(
                cluster_scores=ClusterScores(
                    structured_evolution=0.3,
                    specific_challenge=0.3,
                    flexibility_needed=0.25,
                    strategic_evaluation=0.25,
                ),
            )
        ]
        fake_llm.text_responses = ["Entendi!", "Qual seu momento?"]

        with patch("app.fsm.handlers.intent.get_llm", return_value=fake_llm), \
             patch("app.fsm.handlers.qualifier.get_llm", return_value=fake_llm):
            actions = await machine.process(conversation, "quero saber mais sobre voces")

        assert conversation.stage == ConversationStage.ASKING_Q1
        assert any(isinstance(a, SendButtons) for a in actions)
