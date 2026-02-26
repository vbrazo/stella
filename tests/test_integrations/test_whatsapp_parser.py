from app.integrations.whatsapp.parser import parse_webhook_payload


def test_parse_text_message():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"wa_id": "5511999999999", "profile": {"name": "João"}}],
                    "messages": [{
                        "from": "5511999999999",
                        "id": "msg_123",
                        "type": "text",
                        "text": {"body": "Olá, quero saber mais"},
                        "timestamp": "1708000000",
                    }],
                }
            }]
        }]
    }
    messages = parse_webhook_payload(payload)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.phone == "5511999999999"
    assert msg.name == "João"
    assert msg.type == "text"
    assert msg.text == "Olá, quero saber mais"
    assert msg.message_id == "msg_123"


def test_parse_audio_message():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"wa_id": "5511888888888", "profile": {"name": "Maria"}}],
                    "messages": [{
                        "from": "5511888888888",
                        "id": "msg_456",
                        "type": "audio",
                        "audio": {"id": "audio_789"},
                        "timestamp": "1708000001",
                    }],
                }
            }]
        }]
    }
    messages = parse_webhook_payload(payload)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.type == "audio"
    assert msg.audio_id == "audio_789"


def test_parse_button_reply():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"wa_id": "5511777777777", "profile": {"name": "Pedro"}}],
                    "messages": [{
                        "from": "5511777777777",
                        "id": "msg_789",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "q1_evolution", "title": "Jornada de 12 meses"},
                        },
                        "timestamp": "1708000002",
                    }],
                }
            }]
        }]
    }
    messages = parse_webhook_payload(payload)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.type == "interactive"
    assert msg.button_reply_id == "q1_evolution"
    assert msg.text == "Jornada de 12 meses"


def test_parse_empty_payload():
    payload = {"entry": []}
    messages = parse_webhook_payload(payload)
    assert len(messages) == 0


def test_ignores_non_whatsapp():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "facebook",
                    "messages": [{"from": "123", "id": "m1", "type": "text", "text": {"body": "hi"}}],
                }
            }]
        }]
    }
    messages = parse_webhook_payload(payload)
    assert len(messages) == 0
