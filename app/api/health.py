from fastapi import APIRouter

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    db = get_db()
    await db.command("ping")
    return {"status": "ok", "service": "stella"}
