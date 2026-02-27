from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_database]

    await _db.conversations.create_index("phone", unique=True)
    await _db.conversations.create_index("updated_at")
    await _db.leads.create_index("phone")
    await _db.leads.create_index("kommo_id", sparse=True)

    # Metrics
    await _db.metrics_events.create_index([("type", 1), ("timestamp", -1)])
    await _db.metrics_events.create_index("timestamp")


async def disconnect() -> None:
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _db
