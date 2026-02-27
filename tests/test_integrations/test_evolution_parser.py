"""Tests for Evolution API v2 webhook parsing."""

from app.integrations.whatsapp.evolution_parser import parse_evolution_webhook


def test_parse_text_message():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "id": "msg_123",
                "fromMe": False,
            },
            "message": {"conversation": "Ola quero saber mais"},
            "pushName": "Joao",
        },
    }
    messages = parse_evolution_webhook(payload)
    assert len(messages) == 1
    assert messages[0].phone == "5511999999999"
    assert messages[0].text == "Ola quero saber mais"
    assert messages[0].name == "Joao"
    assert messages[0].type == "text"
    assert messages[0].message_id == "msg_123"


def test_parse_extended_text_message():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511888888888@s.whatsapp.net", "id": "msg_456", "fromMe": False},
            "message": {"extendedTextMessage": {"text": "Uma mensagem longa com link"}},
            "pushName": "Maria",
        },
    }
    messages = parse_evolution_webhook(payload)
    assert len(messages) == 1
    assert messages[0].text == "Uma mensagem longa com link"
    assert messages[0].type == "text"


def test_parse_audio_message():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg_789", "fromMe": False},
            "message": {"audioMessage": {"mimetype": "audio/ogg"}},
            "pushName": "Joao",
        },
    }
    messages = parse_evolution_webhook(payload)
    assert len(messages) == 1
    assert messages[0].type == "audio"
    assert messages[0].audio_id == "msg_789"


def test_parse_button_reply():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg_btn", "fromMe": False},
            "message": {
                "buttonsResponseMessage": {
                    "selectedButtonId": "q1_evolution",
                    "selectedDisplayText": "Jornada de 12 meses",
                }
            },
            "pushName": "Joao",
        },
    }
    messages = parse_evolution_webhook(payload)
    assert len(messages) == 1
    assert messages[0].type == "interactive"
    assert messages[0].button_reply_id == "q1_evolution"
    assert messages[0].button_reply_title == "Jornada de 12 meses"


def test_ignore_non_message_events():
    payload = {"event": "connection.update", "data": {"state": "open"}}
    messages = parse_evolution_webhook(payload)
    assert messages == []


def test_ignore_outgoing_messages():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "id": "msg_out",
                "fromMe": True,
            },
            "message": {"conversation": "Oi, sou a Stella"},
            "pushName": "Stella",
        },
    }
    messages = parse_evolution_webhook(payload)
    assert messages == []


def test_unknown_message_type():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg_unk", "fromMe": False},
            "message": {"stickerMessage": {"mimetype": "image/webp"}},
            "pushName": "Joao",
        },
    }
    messages = parse_evolution_webhook(payload)
    assert len(messages) == 1
    assert messages[0].type == "unknown"
