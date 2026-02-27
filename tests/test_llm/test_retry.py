"""Tests for LLM complete_json_safe retry logic."""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ValidationError

from app.llm.base import MAX_JSON_RETRIES, LLMProvider


class SampleSchema(BaseModel):
    value: str
    score: float


class FakeProvider(LLMProvider):
    """Concrete provider for testing the base class retry."""

    def __init__(self):
        self.complete_json_mock = AsyncMock()

    async def complete_text(self, system, messages, temperature=0.7):
        return "text"

    async def complete_json(self, system, messages, schema, temperature=0.3):
        return await self.complete_json_mock(system, messages, schema, temperature)


@pytest.mark.asyncio
async def test_succeeds_on_first_try():
    provider = FakeProvider()
    expected = SampleSchema(value="test", score=0.9)
    provider.complete_json_mock.return_value = expected

    result = await provider.complete_json_safe(
        system="sys", messages=[], schema=SampleSchema
    )

    assert result == expected
    assert provider.complete_json_mock.call_count == 1


@pytest.mark.asyncio
async def test_retries_on_validation_error_then_succeeds():
    provider = FakeProvider()
    expected = SampleSchema(value="test", score=0.9)
    provider.complete_json_mock.side_effect = [
        ValidationError.from_exception_data("test", []),
        expected,
    ]

    result = await provider.complete_json_safe(
        system="sys", messages=[], schema=SampleSchema
    )

    assert result == expected
    assert provider.complete_json_mock.call_count == 2


@pytest.mark.asyncio
async def test_raises_after_max_retries_exhausted():
    provider = FakeProvider()
    provider.complete_json_mock.side_effect = ValueError("bad json")

    with pytest.raises(ValueError, match="bad json"):
        await provider.complete_json_safe(
            system="sys", messages=[], schema=SampleSchema
        )

    assert provider.complete_json_mock.call_count == MAX_JSON_RETRIES + 1


@pytest.mark.asyncio
async def test_temperature_decreases_on_retries():
    provider = FakeProvider()
    expected = SampleSchema(value="ok", score=0.5)
    provider.complete_json_mock.side_effect = [
        ValueError("attempt 1"),
        ValueError("attempt 2"),
        expected,
    ]

    result = await provider.complete_json_safe(
        system="sys", messages=[], schema=SampleSchema, temperature=0.3
    )

    assert result == expected
    temperatures = [call.args[3] for call in provider.complete_json_mock.call_args_list]
    assert temperatures[0] == 0.3
    assert temperatures[1] == 0.2
    assert temperatures[2] == 0.1
