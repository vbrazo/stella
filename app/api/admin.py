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
