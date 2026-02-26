from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class ConversationStage(StrEnum):
    IDLE = "idle"
    OPENING_SENT = "opening_sent"
    AWAITING_INTENT = "awaiting_intent"
    CONFIRMING = "confirming"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    ASKING_Q1 = "asking_q1"
    AWAITING_Q1 = "awaiting_q1"
    ASKING_Q2 = "asking_q2"
    AWAITING_Q2 = "awaiting_q2"
    ASKING_Q3 = "asking_q3"
    AWAITING_Q3 = "awaiting_q3"
    RECOMMENDING = "recommending"
    CARD_SENT = "card_sent"
    AWAITING_DECISION = "awaiting_decision"
    HANDLING_OBJECTION = "handling_objection"
    PRICE_FALLBACK = "price_fallback"
    ESCALATED = "escalated"
    COMPLETED = "completed"


class Message(BaseModel):
    direction: str  # "inbound" | "outbound"
    type: str  # "text" | "audio" | "interactive" | "card" | "button"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)


class Conversation(BaseModel):
    phone: str
    stage: ConversationStage = ConversationStage.IDLE
    messages: list[Message] = Field(default_factory=list)
    seen_message_ids: list[str] = Field(default_factory=list)

    # Lead enrichment data
    lead_data: dict = Field(default_factory=dict)

    # Cluster classification
    cluster_scores: dict[str, float] = Field(default_factory=dict)
    dominant_cluster: str | None = None

    # Qualification tracking
    structured_question_count: int = 0
    q1_answer: str | None = None
    q2_answer: str | None = None
    q3_answer: str | None = None

    # Recommendation
    product_recommended: str | None = None
    product_alternative: str | None = None
    card_sent: bool = False

    # Price fallback
    price_ask_count: int = 0

    # Escalation
    escalated: bool = False
    escalation_reason: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def inbound_messages(self) -> list[Message]:
        return [m for m in self.messages if m.direction == "inbound"]

    def last_inbound_text(self) -> str | None:
        for m in reversed(self.messages):
            if m.direction == "inbound" and m.type in ("text", "audio"):
                return m.content
        return None
