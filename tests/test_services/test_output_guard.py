"""Tests for output_guard module."""

from app.services.output_guard import (
    FALLBACK_MESSAGES,
    enforce_length,
    enforce_single_idea,
    guard_output,
)


class TestEnforceLength:
    def test_short_text_unchanged(self):
        text = "Oi, como posso ajudar?"
        assert enforce_length(text) == text

    def test_exactly_140_chars_unchanged(self):
        text = "a" * 140
        assert enforce_length(text) == text

    def test_over_140_truncates_at_sentence_boundary(self):
        text = "Primeira frase. " + "a" * 130
        result = enforce_length(text)
        assert len(result) <= 140
        assert result.endswith(".")

    def test_over_140_hard_truncate_when_no_boundary(self):
        text = "a" * 200
        result = enforce_length(text)
        assert len(result) <= 140
        assert result.endswith("...")

    def test_truncates_at_question_mark(self):
        text = "Voce esta pronto? " + "a" * 130
        result = enforce_length(text)
        assert result.endswith("?")

    def test_custom_max_chars(self):
        text = "a" * 60
        result = enforce_length(text, max_chars=50)
        assert len(result) <= 50


class TestEnforceSingleIdea:
    def test_one_sentence_unchanged(self):
        text = "Oi, como posso ajudar?"
        assert enforce_single_idea(text) == text

    def test_two_sentences_unchanged(self):
        text = "Primeira frase. Segunda frase."
        assert enforce_single_idea(text) == text

    def test_three_sentences_truncated_to_two(self):
        text = "Primeira frase. Segunda frase. Terceira frase."
        result = enforce_single_idea(text)
        assert result == "Primeira frase. Segunda frase."

    def test_four_sentences_truncated_to_two(self):
        text = "Um. Dois. Tres. Quatro."
        result = enforce_single_idea(text)
        assert result == "Um. Dois."


class TestGuardOutput:
    def test_empty_string_returns_fallback(self):
        assert guard_output("") == FALLBACK_MESSAGES["generic"]

    def test_whitespace_only_returns_fallback(self):
        assert guard_output("   ") == FALLBACK_MESSAGES["generic"]

    def test_empty_with_context_returns_context_fallback(self):
        assert guard_output("", context="opening") == FALLBACK_MESSAGES["opening"]

    def test_normal_text_passes_through(self):
        text = "Entendi seu momento."
        assert guard_output(text) == text

    def test_long_multi_sentence_gets_truncated(self):
        text = "Primeira frase. Segunda frase. Terceira frase. " + "a" * 100
        result = guard_output(text)
        assert len(result) <= 140

    def test_strips_whitespace(self):
        assert guard_output("  Oi  ") == "Oi"
