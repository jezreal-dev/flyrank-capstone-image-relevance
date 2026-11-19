"""Human review workflow service for approving, rejecting, and inspecting recommendations."""
import uuid
from typing import Dict, Any, List
from app.core.database import get_db_connection
from app.models.matching_schema import ReviewDecisionEnum, ReviewActionResponse

class ReviewService:
    def record_decision(
        self,
        suggestion_id: str,
        decision: ReviewDecisionEnum,
        reviewer_notes: str | None = None
    ) -> ReviewActionResponse:
        with get_db_connection() as conn:
            # Check suggestion exists
            sug = conn.execute("SELECT id FROM suggestions WHERE id = ?", (suggestion_id,)).fetchone()
            if not sug:
                raise ValueError(f"Suggestion with ID '{suggestion_id}' does not exist")

            review_id = f"rev_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO review_decisions (id, suggestion_id, decision, reviewer_notes)
                VALUES (?, ?, ?, ?)
                """,
                (review_id, suggestion_id, decision.value, reviewer_notes)
            )
            conn.commit()

            row = conn.execute(
                "SELECT id, suggestion_id, decision, reviewer_notes, decided_at FROM review_decisions WHERE id = ?",
                (review_id,)
            ).fetchone()

            return ReviewActionResponse(
                id=row["id"],
                suggestion_id=row["suggestion_id"],
                decision=ReviewDecisionEnum(row["decision"]),
                reviewer_notes=row["reviewer_notes"],
                decided_at=row["decided_at"]
            )

    def get_review_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT 
                    r.id, r.suggestion_id, r.decision, r.reviewer_notes, r.decided_at,
                    s.post_id, s.image_id, s.similarity_score, s.guard_decision, s.explanation
                FROM review_decisions r
                JOIN suggestions s ON r.suggestion_id = s.id
                ORDER BY r.decided_at DESC LIMIT ?
                """,
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

review_service = ReviewService()
