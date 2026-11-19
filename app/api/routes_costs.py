"""API routes for cost tracking and budget telemetry."""
from fastapi import APIRouter
from app.core.cost_tracker import tracker
from app.core.database import get_db_connection

router = APIRouter(prefix="/api/costs", tags=["costs"])

@router.get("/summary")
def get_cost_summary():
    return tracker.get_summary()

@router.get("/log")
def get_recent_cost_events(limit: int = 50):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM cost_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
