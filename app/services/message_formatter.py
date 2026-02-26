"""WhatsApp Brazil message formatting: 140 char limit, split, delays."""

import asyncio
import random


def split_message(text: str, max_chars: int = 140) -> list[str]:
    """Split a long message into WhatsApp-friendly chunks."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    # Try to split on sentence boundaries first
    sentences = text.replace(". ", ".\n").split("\n")

    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If single sentence is too long, split by words (or hard-split)
            if len(sentence) > max_chars:
                chunks.extend(_split_by_words(sentence, max_chars))
                current_chunk = ""
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_by_words(text: str, max_chars: int) -> list[str]:
    """Split text by words when sentence is too long."""
    words = text.split()
    chunks: list[str] = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip() if current else word
        else:
            if current:
                chunks.append(current)
            # If a single word exceeds max_chars, hard-split it
            if len(word) > max_chars:
                for i in range(0, len(word), max_chars):
                    chunks.append(word[i : i + max_chars])
                current = ""
            else:
                current = word

    if current:
        chunks.append(current)
    return chunks


async def whatsapp_delay() -> None:
    """Simulate human typing delay (600ms - 2200ms)."""
    delay = random.uniform(0.6, 2.2)
    await asyncio.sleep(delay)
