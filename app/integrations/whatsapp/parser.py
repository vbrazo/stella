import logging

from app.integrations.whatsapp.models import IncomingMessage

logger = logging.getLogger(__name__)


def parse_webhook_payload(payload: dict) -> list[IncomingMessage]:
    """Parse Meta WhatsApp Cloud API webhook payload into IncomingMessage objects."""
    messages: list[IncomingMessage] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") != "whatsapp":
                continue

            contacts = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}

            for msg in value.get("messages", []):
                try:
                    parsed = _parse_single_message(msg, contacts)
                    if parsed:
                        messages.append(parsed)
                except Exception:
                    logger.exception("Failed to parse message: %s", msg)

    return messages


def _parse_single_message(msg: dict, contacts: dict[str, str | None]) -> IncomingMessage | None:
    phone = msg.get("from", "")
    message_id = msg.get("id", "")
    msg_type = msg.get("type", "unknown")
    name = contacts.get(phone)
    timestamp = msg.get("timestamp")

    if msg_type == "text":
        return IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=name,
            type="text",
            text=msg["text"]["body"],
            timestamp=timestamp,
        )

    if msg_type == "audio":
        return IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=name,
            type="audio",
            audio_id=msg["audio"]["id"],
            timestamp=timestamp,
        )

    if msg_type == "interactive":
        interactive = msg.get("interactive", {})
        interactive_type = interactive.get("type")

        if interactive_type == "button_reply":
            reply = interactive["button_reply"]
            return IncomingMessage(
                message_id=message_id,
                phone=phone,
                name=name,
                type="interactive",
                button_reply_id=reply["id"],
                button_reply_title=reply["title"],
                text=reply["title"],
                timestamp=timestamp,
            )

        if interactive_type == "list_reply":
            reply = interactive["list_reply"]
            return IncomingMessage(
                message_id=message_id,
                phone=phone,
                name=name,
                type="interactive",
                list_reply_id=reply["id"],
                list_reply_title=reply["title"],
                text=reply["title"],
                timestamp=timestamp,
            )

    if msg_type == "button":
        return IncomingMessage(
            message_id=message_id,
            phone=phone,
            name=name,
            type="button",
            text=msg.get("button", {}).get("text"),
            timestamp=timestamp,
        )

    logger.info("Unsupported message type: %s", msg_type)
    return IncomingMessage(
        message_id=message_id,
        phone=phone,
        name=name,
        type="unknown",
        timestamp=timestamp,
    )
