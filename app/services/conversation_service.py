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
from app.services.metrics import get_metrics, timed_operation
from app.services.output_guard import guard_output

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
    metrics = get_metrics()

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
        except Exception as e:
            logger.exception("Audio transcription failed for %s", incoming.audio_id)
            await metrics.record_integration_error(
                integration="whisper",
                operation="transcribe_audio",
                error=str(e),
                phone=phone,
            )
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

    # Run FSM with timing
    machine = _get_machine()
    old_stage = conversation.stage

    async with timed_operation("fsm_process") as timing:
        actions = await machine.process(conversation, message_text)

    # Record handler timing
    await metrics.record_handler_timing(
        handler_name=old_stage.value,
        duration_ms=timing["elapsed_ms"],
        phone=phone,
        stage=old_stage.value,
    )

    # Record stage transitions
    for action in actions:
        if isinstance(action, UpdateStage):
            await metrics.record_stage_transition(
                phone=phone,
                from_stage=old_stage.value,
                to_stage=action.stage.value,
                handler_name=old_stage.value,
                duration_ms=timing["elapsed_ms"],
            )

    # Execute actions
    for action in actions:
        await _execute_action(phone, conversation, action)

    # Record conversation outcome on terminal states
    if conversation.stage in (ConversationStage.COMPLETED, ConversationStage.ESCALATED):
        duration = (conversation.updated_at - conversation.created_at).total_seconds()
        outcome = "completed" if conversation.stage == ConversationStage.COMPLETED else "escalated"
        await metrics.record_conversation_outcome(
            phone=phone,
            outcome=outcome,
            final_stage=conversation.stage.value,
            product_recommended=conversation.product_recommended,
            duration_seconds=duration,
        )

    # Persist conversation
    await _save_conversation(db, conversation)


async def _execute_action(phone: str, conversation: Conversation, action: Action) -> None:
    """Execute a single FSM action."""
    metrics = get_metrics()

    if isinstance(action, SendText):
        # Apply guardrails then split for WhatsApp
        guarded_text = guard_output(action.text)
        chunks = split_message(guarded_text)
        for chunk in chunks:
            await whatsapp_delay()
            try:
                await wa_client.send_text(phone, chunk)
            except Exception as e:
                logger.exception("Failed to send text to %s", phone)
                await metrics.record_integration_error(
                    integration="whatsapp",
                    operation="send_text",
                    error=str(e),
                    phone=phone,
                )
                return

            # Record outbound message
            conversation.add_message(Message(
                direction="outbound",
                type="text",
                content=chunk,
            ))

    elif isinstance(action, SendButtons):
        await whatsapp_delay()
        guarded_body = guard_output(action.body, context="qualifier")
        try:
            await wa_client.send_buttons(phone, guarded_body, action.buttons)
        except Exception as e:
            logger.exception("Failed to send buttons to %s", phone)
            await metrics.record_integration_error(
                integration="whatsapp",
                operation="send_buttons",
                error=str(e),
                phone=phone,
            )
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
        except Exception as e:
            logger.exception("Failed to send card to %s", phone)
            await metrics.record_integration_error(
                integration="whatsapp",
                operation="send_cta_card",
                error=str(e),
                phone=phone,
            )
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
            except Exception as e:
                logger.exception("Failed to log escalation to Kommo")
                await metrics.record_integration_error(
                    integration="kommo",
                    operation="escalation_log",
                    error=str(e),
                    phone=phone,
                )

    elif isinstance(action, LogCRM):
        logger.info("CRM log for %s: %s", phone, action.data)
        kommo = KommoClient()
        if kommo.configured and conversation.lead_data.get("kommo_lead_id"):
            try:
                lead_id = conversation.lead_data["kommo_lead_id"]
                note = "\n".join(f"{k}: {v}" for k, v in action.data.items())
                await kommo.add_note("leads", lead_id, note)
            except Exception as e:
                logger.exception("Failed to log to Kommo")
                await metrics.record_integration_error(
                    integration="kommo",
                    operation="add_note",
                    error=str(e),
                    phone=phone,
                )

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
