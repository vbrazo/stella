from pydantic import BaseModel


class IncomingMessage(BaseModel):
    """Parsed incoming WhatsApp message."""

    message_id: str
    phone: str
    name: str | None = None
    type: str  # "text" | "audio" | "interactive" | "button" | "image" | "unknown"
    text: str | None = None
    audio_id: str | None = None
    button_reply_id: str | None = None
    button_reply_title: str | None = None
    list_reply_id: str | None = None
    list_reply_title: str | None = None
    timestamp: str | None = None


class InteractiveButton(BaseModel):
    id: str
    title: str  # Max 20 chars


class InteractiveCard(BaseModel):
    """WhatsApp interactive message with CTA URL button."""

    header_text: str | None = None
    body_text: str
    footer_text: str | None = None
    button_text: str  # Max 20 chars
    button_url: str
