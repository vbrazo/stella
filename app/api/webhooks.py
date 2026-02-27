import logging

from fastapi import APIRouter, Query, Request, Response

from app.config import settings
from app.integrations.whatsapp.parser import parse_webhook_payload
from app.services.conversation_service import handle_incoming_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
async def verify_webhook(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
):
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    logger.warning("Webhook verification failed: invalid token")
    return Response(content="Forbidden", status_code=403)


@router.post("/whatsapp")
async def receive_message(request: Request):
    body = await request.json()

    if settings.whatsapp_provider == "evolution":
        from app.integrations.whatsapp.evolution_parser import parse_evolution_webhook

        messages = parse_evolution_webhook(body)
    else:
        messages = parse_webhook_payload(body)

    for msg in messages:
        try:
            await handle_incoming_message(msg)
        except Exception:
            logger.exception("Error processing message from %s", msg.phone)

    return {"status": "ok"}
