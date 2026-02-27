"""Evolution API v2 webhook parser."""

import logging

from app.integrations.whatsapp.models import IncomingMessage

logger = logging.getLogger(__name__)


def parse_evolution_webhook(payload: dict) -> list[IncomingMessage]:
    """Parse Evolution API v2 webhook payload into IncomingMessage objects."""
    messages: list[IncomingMessage] = []

    event = payload.get("event", "")
    if event != "messages.upsert":
        return messages

    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})
    raw_jid = key.get("remoteJid", "")
    phone = raw_jid.replace("@s.whatsapp.net", "")
    message_id = key.get("id", "")
    push_name = data.get("pushName")

    # Skip outgoing messages
    if key.get("fromMe", False):
        return messages

    if "conversation" in message:
        messages.append(IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=push_name,
            type="text",
            text=message["conversation"],
        ))
    elif "extendedTextMessage" in message:
        messages.append(IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=push_name,
            type="text",
            text=message["extendedTextMessage"].get("text", ""),
        ))
    elif "audioMessage" in message:
        messages.append(IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=push_name,
            type="audio",
            audio_id=message_id,
        ))
    elif "buttonsResponseMessage" in message:
        btn = message["buttonsResponseMessage"]
        messages.append(IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=push_name,
            type="interactive",
            button_reply_id=btn.get("selectedButtonId", ""),
            button_reply_title=btn.get("selectedDisplayText", ""),
            text=btn.get("selectedDisplayText", ""),
        ))
    else:
        logger.info("Unsupported Evolution message type: %s", list(message.keys()))
        messages.append(IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=push_name,
            type="unknown",
        ))

    return messages
