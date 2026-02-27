from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/conversations/{phone}")
async def get_conversation(phone: str):
    db = get_db()
    conversation = await db.conversations.find_one({"phone": phone}, {"_id": 0})
    if not conversation:
        return {"error": "Conversation not found"}
    return conversation


@router.get("/conversations")
async def list_conversations(limit: int = 20, skip: int = 0):
    db = get_db()
    cursor = db.conversations.find(
        {},
        {"_id": 0, "phone": 1, "stage": 1, "lead_data.name": 1, "updated_at": 1},
    ).sort("updated_at", -1).skip(skip).limit(limit)
    conversations = await cursor.to_list(length=limit)
    return {"conversations": conversations, "count": len(conversations)}


# --- Metrics ---


@router.get("/metrics/funnel")
async def get_funnel_metrics(hours: int = 24):
    """Stage drop-off funnel for the last N hours."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    pipeline = [
        {"$match": {"type": "stage_transition", "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"from": "$from_stage", "to": "$to_stage"},
            "count": {"$sum": 1},
            "avg_duration_ms": {"$avg": "$duration_ms"},
        }},
        {"$sort": {"count": -1}},
    ]
    results = await db.metrics_events.aggregate(pipeline).to_list(100)
    return {"funnel": results, "period_hours": hours}


@router.get("/metrics/outcomes")
async def get_outcome_metrics(hours: int = 24):
    """Conversion outcomes for the last N hours."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    pipeline = [
        {"$match": {"type": "conversation_outcome", "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$outcome",
            "count": {"$sum": 1},
            "avg_duration_seconds": {"$avg": "$duration_seconds"},
        }},
    ]
    results = await db.metrics_events.aggregate(pipeline).to_list(10)
    return {"outcomes": results, "period_hours": hours}


@router.get("/metrics/errors")
async def get_error_metrics(hours: int = 24):
    """Integration error rates for the last N hours."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    pipeline = [
        {"$match": {"type": "integration_error", "timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"integration": "$integration", "operation": "$operation"},
            "count": {"$sum": 1},
            "last_error": {"$last": "$error"},
        }},
        {"$sort": {"count": -1}},
    ]
    results = await db.metrics_events.aggregate(pipeline).to_list(50)
    return {"errors": results, "period_hours": hours}
