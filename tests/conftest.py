import os

# Set test environment variables before importing app
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DATABASE", "stella_test")
os.environ.setdefault("WHATSAPP_TOKEN", "test_token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test_phone_id")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test_verify")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("KOMMO_API_TOKEN", "")
os.environ.setdefault("RELEVANCE_AI_API_URL", "")
os.environ.setdefault("RELEVANCE_AI_AUTHORIZATION_TOKEN", "")

import pytest

from app.engine.classifier import ClusterScores, IntentAnalysis
from app.fsm.machine import StateMachine
from app.models.conversation import Conversation


class FakeLLM:
    """Deterministic LLM for testing. Returns pre-configured responses."""

    def __init__(self):
        self.text_responses: list[str] = []
        self.json_responses: list[object] = []
        self._text_idx = 0
        self._json_idx = 0

    async def complete_text(self, system, messages, temperature=0.7):
        if self._text_idx < len(self.text_responses):
            resp = self.text_responses[self._text_idx]
            self._text_idx += 1
            return resp
        return "Resposta de teste."

    async def complete_json(self, system, messages, schema, temperature=0.3):
        if self._json_idx < len(self.json_responses):
            resp = self.json_responses[self._json_idx]
            self._json_idx += 1
            return resp
        # Return a safe default IntentAnalysis
        return IntentAnalysis(
            cluster_scores=ClusterScores(
                structured_evolution=0.25,
                specific_challenge=0.25,
                flexibility_needed=0.25,
                strategic_evaluation=0.25,
            ),
        )

    async def complete_json_safe(self, system, messages, schema, temperature=0.3):
        return await self.complete_json(system, messages, schema, temperature)


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def conversation():
    return Conversation(phone="5511999999999")


@pytest.fixture
def machine():
    return StateMachine()
