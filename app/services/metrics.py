"""Lightweight async metrics that write to MongoDB."""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from app.database import get_db

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects FSM, conversion, and integration metrics into MongoDB."""

    async def record_stage_transition(
        self,
        phone: str,
        from_stage: str,
        to_stage: str,
        handler_name: str,
        duration_ms: float,
    ) -> None:
        db = get_db()
        await db.metrics_events.insert_one({
            "type": "stage_transition",
            "phone": phone,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "handler": handler_name,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc),
        })

    async def record_conversation_outcome(
        self,
        phone: str,
        outcome: str,
        final_stage: str,
        product_recommended: str | None,
        duration_seconds: float,
    ) -> None:
        db = get_db()
        await db.metrics_events.insert_one({
            "type": "conversation_outcome",
            "phone": phone,
            "outcome": outcome,
            "final_stage": final_stage,
            "product_recommended": product_recommended,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc),
        })

    async def record_integration_error(
        self,
        integration: str,
        operation: str,
        error: str,
        phone: str | None = None,
    ) -> None:
        db = get_db()
        await db.metrics_events.insert_one({
            "type": "integration_error",
            "integration": integration,
            "operation": operation,
            "error": str(error)[:500],
            "phone": phone,
            "timestamp": datetime.now(timezone.utc),
        })

    async def record_handler_timing(
        self,
        handler_name: str,
        duration_ms: float,
        phone: str,
        stage: str,
    ) -> None:
        db = get_db()
        await db.metrics_events.insert_one({
            "type": "handler_timing",
            "handler": handler_name,
            "duration_ms": duration_ms,
            "phone": phone,
            "stage": stage,
            "timestamp": datetime.now(timezone.utc),
        })


@asynccontextmanager
async def timed_operation(label: str):
    """Context manager that yields a dict with elapsed_ms after exit."""
    result = {"elapsed_ms": 0.0}
    start = time.monotonic()
    try:
        yield result
    finally:
        result["elapsed_ms"] = (time.monotonic() - start) * 1000


_collector: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
