import logging
import tempfile

from openai import AsyncOpenAI

from app.config import settings
from app.integrations.whatsapp import client as wa_client

logger = logging.getLogger(__name__)

_openai: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai
    if _openai is None:
        _openai = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai


async def transcribe_audio(audio_id: str) -> str:
    """Download audio from WhatsApp and transcribe with Whisper."""
    audio_bytes = await wa_client.download_media(audio_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as f:
        f.write(audio_bytes)
        f.flush()

        client = _get_openai()
        with open(f.name, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt",
            )

    logger.info("Transcribed audio %s: %d chars", audio_id, len(transcription.text))
    return transcription.text
