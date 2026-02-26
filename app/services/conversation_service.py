"""Main orchestrator: webhook → FSM → response."""

import logging
from datetime import datetime, timezone

from app.database import get_db
from app.fsm.machine import (
    Action,
    Escalate,
    LogCRM,
    SendButtons,
    SendCard,
    SendText,
    StateMachine,
    UpdateStage,
)
from app.integrations.kommo.client import KommoClient
from app.integrations.whatsapp import client as wa_client
from app.integrations.whatsapp.models import IncomingMessage
from app.integrations.whisper.client import transcribe_audio
from app.models.conversation import Conversation, ConversationStage, Message
from app.services.message_formatter import split_message, whatsapp_delay

logger = logging.getLogger(__name__)

_machine: StateMachine | None = None


def _get_machine() -> StateMachine:
    global _machine
    if _machine is None:
        _machine = StateMachine()
    return _machine


async def handle_incoming_message(incoming: IncomingMessage) -> None:
    """Process a single incoming WhatsApp message end-to-end."""
    db = get_db()
    phone = incoming.phone

    # Mark as read
    try:
        await wa_client.mark_as_read(incoming.message_id)
    except Exception:
        logger.warning("Failed to mark message as read: %s", incoming.message_id)

    # Get or create conversation
    conversation = await _get_or_create_conversation(db, phone, incoming)

    # Deduplicate
    if incoming.message_id in conversation.seen_message_ids:
        logger.info("Duplicate message %s, skipping", incoming.message_id)
        return
    conversation.seen_message_ids.append(incoming.message_id)

    # Transcribe audio if needed
    message_text = incoming.text or ""
    if incoming.type == "audio" and incoming.audio_id:
        try:
            message_text = await transcribe_audio(incoming.audio_id)
        except Exception:
            logger.exception("Audio transcription failed for %s", incoming.audio_id)
            message_text = ""
            await wa_client.send_text(phone, "Não consegui ouvir o áudio. Pode mandar por texto?")
            return

    if not message_text.strip():
        logger.info("Empty message from %s, skipping", phone)
        return

    # Record inbound message
    conversation.add_message(Message(
        direction="inbound",
        type=incoming.type,
        content=message_text,
        metadata={"message_id": incoming.message_id, "name": incoming.name},
    ))

    # Enrich lead data if we have new info (LinkedIn URL, etc.)
    if incoming.name and not conversation.lead_data.get("name"):
        conversation.lead_data["name"] = incoming.name

    # Run FSM
    machine = _get_machine()

    # For IDLE state, process without message (trigger opening)
    if conversation.stage == ConversationStage.IDLE:
        actions = await machine.process(conversation, message_text)
    else:
        actions = await machine.process(conversation, message_text)

    # Execute actions
    for action in actions:
        await _execute_action(phone, conversation, action)

    # Persist conversation
    await _save_conversation(db, conversation)


async def _execute_action(phone: str, conversation: Conversation, action: Action) -> None:
    """Execute a single FSM action."""
    if isinstance(action, SendText):
        # Split long messages for WhatsApp
        chunks = split_message(action.text)
        for chunk in chunks:
            await whatsapp_delay()
            try:
                await wa_client.send_text(phone, chunk)
            except Exception:
                logger.exception("Failed to send text to %s", phone)
                return

            # Record outbound message
            conversation.add_message(Message(
                direction="outbound",
                type="text",
                content=chunk,
            ))

    elif isinstance(action, SendButtons):
        await whatsapp_delay()
        try:
            await wa_client.send_buttons(phone, action.body, action.buttons)
        except Exception:
            logger.exception("Failed to send buttons to %s", phone)
            return

        conversation.add_message(Message(
            direction="outbound",
            type="interactive",
            content=action.body,
        ))

    elif isinstance(action, SendCard):
        await whatsapp_delay()
        try:
            await wa_client.send_cta_card(phone, action.card)
        except Exception:
            logger.exception("Failed to send card to %s", phone)
            return

        conversation.add_message(Message(
            direction="outbound",
            type="card",
            content=action.card.body_text,
            metadata={"url": action.card.button_url},
        ))

    elif isinstance(action, Escalate):
        conversation.escalated = True
        conversation.escalation_reason = action.reason
        logger.info("Escalating %s: %s", phone, action.reason)

        # Log to Kommo
        kommo = KommoClient()
        if kommo.configured and conversation.lead_data.get("kommo_lead_id"):
            try:
                lead_id = conversation.lead_data["kommo_lead_id"]
                await kommo.add_note("leads", lead_id, f"Stella escalation: {action.reason}")
                await kommo.update_lead_tags(lead_id, ["stella_escalated"])
            except Exception:
                logger.exception("Failed to log escalation to Kommo")

    elif isinstance(action, LogCRM):
        logger.info("CRM log for %s: %s", phone, action.data)
        kommo = KommoClient()
        if kommo.configured and conversation.lead_data.get("kommo_lead_id"):
            try:
                lead_id = conversation.lead_data["kommo_lead_id"]
                note = "\n".join(f"{k}: {v}" for k, v in action.data.items())
                await kommo.add_note("leads", lead_id, note)
            except Exception:
                logger.exception("Failed to log to Kommo")

    elif isinstance(action, UpdateStage):
        # Stage already updated by machine, just log
        logger.info("Stage transition for %s: -> %s", phone, action.stage)


async def _get_or_create_conversation(db, phone: str, incoming: IncomingMessage) -> Conversation:
    """Load existing conversation or create new one."""
    doc = await db.conversations.find_one({"phone": phone})

    if doc:
        doc.pop("_id", None)
        return Conversation(**doc)

    # New conversation
    conversation = Conversation(phone=phone)
    if incoming.name:
        conversation.lead_data["name"] = incoming.name

    return conversation


async def _save_conversation(db, conversation: Conversation) -> None:
    """Upsert conversation to MongoDB."""
    conversation.updated_at = datetime.now(timezone.utc)
    data = conversation.model_dump(mode="json")

    await db.conversations.update_one(
        {"phone": conversation.phone},
        {"$set": data},
        upsert=True,
    )
