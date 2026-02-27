"""Tests for MetricsCollector and timed_operation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.metrics import MetricsCollector, get_metrics, timed_operation


@pytest.fixture
def mock_db():
    """Mock MongoDB database with metrics_events collection."""
    db = MagicMock()
    db.metrics_events = MagicMock()
    db.metrics_events.insert_one = AsyncMock()
    return db


@pytest.fixture
def collector(mock_db):
    with patch("app.services.metrics.get_db", return_value=mock_db):
        yield MetricsCollector(), mock_db


@pytest.mark.asyncio
async def test_record_stage_transition(collector):
    metrics, mock_db = collector
    with patch("app.services.metrics.get_db", return_value=mock_db):
        await metrics.record_stage_transition(
            phone="5511999999999",
            from_stage="IDLE",
            to_stage="OPENING_SENT",
            handler_name="IDLE",
            duration_ms=150.5,
        )

    mock_db.metrics_events.insert_one.assert_called_once()
    doc = mock_db.metrics_events.insert_one.call_args[0][0]
    assert doc["type"] == "stage_transition"
    assert doc["phone"] == "5511999999999"
    assert doc["from_stage"] == "IDLE"
    assert doc["to_stage"] == "OPENING_SENT"
    assert doc["handler"] == "IDLE"
    assert doc["duration_ms"] == 150.5
    assert "timestamp" in doc


@pytest.mark.asyncio
async def test_record_conversation_outcome(collector):
    metrics, mock_db = collector
    with patch("app.services.metrics.get_db", return_value=mock_db):
        await metrics.record_conversation_outcome(
            phone="5511999999999",
            outcome="completed",
            final_stage="COMPLETED",
            product_recommended="programa_head_tech",
            duration_seconds=3600.0,
        )

    doc = mock_db.metrics_events.insert_one.call_args[0][0]
    assert doc["type"] == "conversation_outcome"
    assert doc["outcome"] == "completed"
    assert doc["product_recommended"] == "programa_head_tech"
    assert doc["duration_seconds"] == 3600.0


@pytest.mark.asyncio
async def test_record_integration_error(collector):
    metrics, mock_db = collector
    with patch("app.services.metrics.get_db", return_value=mock_db):
        await metrics.record_integration_error(
            integration="whatsapp",
            operation="send_text",
            error="Connection timeout" * 100,  # long error string
            phone="5511999999999",
        )

    doc = mock_db.metrics_events.insert_one.call_args[0][0]
    assert doc["type"] == "integration_error"
    assert doc["integration"] == "whatsapp"
    assert doc["operation"] == "send_text"
    assert len(doc["error"]) <= 500  # truncated


@pytest.mark.asyncio
async def test_record_handler_timing(collector):
    metrics, mock_db = collector
    with patch("app.services.metrics.get_db", return_value=mock_db):
        await metrics.record_handler_timing(
            handler_name="AWAITING_INTENT",
            duration_ms=250.3,
            phone="5511999999999",
            stage="AWAITING_INTENT",
        )

    doc = mock_db.metrics_events.insert_one.call_args[0][0]
    assert doc["type"] == "handler_timing"
    assert doc["handler"] == "AWAITING_INTENT"
    assert doc["duration_ms"] == 250.3


@pytest.mark.asyncio
async def test_timed_operation():
    async with timed_operation("test") as timing:
        await asyncio.sleep(0.01)

    assert timing["elapsed_ms"] > 0
    assert timing["elapsed_ms"] >= 10  # at least 10ms from the sleep


def test_get_metrics_returns_singleton():
    """get_metrics always returns the same instance."""
    import app.services.metrics as mod

    mod._collector = None
    m1 = get_metrics()
    m2 = get_metrics()
    assert m1 is m2
    mod._collector = None  # cleanup
