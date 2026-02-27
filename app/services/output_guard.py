"""Post-processing guardrails for LLM text outputs."""

import logging
import re

logger = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 140

FALLBACK_MESSAGES = {
    "opening": "Oi! Sou a Stella da Strides. Como posso te ajudar?",
    "confirmation": "Entendi seu momento. Faz sentido?",
    "qualifier": "Me conta mais sobre seu momento atual.",
    "closer": "Esse caminho faz sentido pra voce?",
    "objection": "Entendo. Posso te mostrar uma alternativa?",
    "generic": "Me conta mais para eu te ajudar melhor.",
}


def enforce_length(text: str, max_chars: int = MAX_MESSAGE_CHARS) -> str:
    """Truncate text at sentence boundary if over max_chars."""
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    last_question = truncated.rfind("?")
    last_excl = truncated.rfind("!")
    best_cut = max(last_period, last_question, last_excl)

    if best_cut > max_chars * 0.5:
        return truncated[: best_cut + 1]

    return truncated[: max_chars - 3] + "..."


def enforce_single_idea(text: str) -> str:
    """If text contains more than 2 sentences, keep only the first two."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 2:
        return text
    return " ".join(sentences[:2])


def guard_output(text: str, context: str = "generic") -> str:
    """Apply all guardrails to an LLM text output."""
    text = text.strip()

    if not text:
        logger.warning("Empty LLM output, using fallback for context=%s", context)
        return FALLBACK_MESSAGES.get(context, FALLBACK_MESSAGES["generic"])

    text = enforce_single_idea(text)
    text = enforce_length(text)

    return text
