"""Semantic image matching and ranking engine with Mismatch Guard integration."""
import json
import uuid
from typing import List, Dict, Any, Optional
from app.core.database import get_db_connection
from app.core.vector_math import cosine_similarity
from app.services.embedding_service import embedding_service
from app.services.mismatch_guard import mismatch_guard
from app.models.matching_schema import (
    PostSuggestionsResponse,
    SuggestionItem,
    GuardDecision
)

class MatchingEngine:
    def rank_and_guard_candidates(
        self,
        post_id: str,
        max_suggestions: int = 5
    ) -> PostSuggestionsResponse:
        with get_db_connection() as conn:
            # 1. Fetch Post details
            post_row = conn.execute(
                "SELECT id, title, slug, content, target_subject FROM posts WHERE id = ?",
                (post_id,)
            ).fetchone()
            if not post_row:
                raise ValueError(f"Post with ID '{post_id}' not found")

            # 2. Fetch or compute Post embedding
            post_vector = embedding_service.get_embedding("post", post_id)
            if not post_vector:
                post_vector = embedding_service.embed_and_store_post(
                    post_id,
                    post_row["title"],
                    post_row["content"],
                    post_row["target_subject"]
                )

            # 3. Fetch all completed images with metadata and embeddings
            candidates_query = """
                SELECT 
                    img.id as image_id,
                    img.url,
                    img.filename,
                    img.status,
                    meta.subject,
                    meta.category,
                    meta.attributes_json,
                    meta.caption,
                    meta.confidence,
                    meta.is_flagged,
                    emb.vector_json
                FROM images img
                JOIN image_metadata meta ON img.id = meta.image_id
                JOIN embeddings emb ON img.id = emb.entity_id AND emb.entity_type = 'image'
                WHERE img.status IN ('completed', 'flagged_for_review')
            """
            image_rows = conn.execute(candidates_query).fetchall()

            # 4. Score all candidates using cosine similarity
            scored_candidates = []
            for row in image_rows:
                img_vector = json.loads(row["vector_json"])
                similarity = cosine_similarity(post_vector, img_vector)
                
                decision, reason = mismatch_guard.evaluate_candidate(
                    post_title=post_row["title"],
                    post_content=post_row["content"],
                    target_subject=post_row["target_subject"],
                    image_subject=row["subject"],
                    image_category=row["category"],
                    image_confidence=float(row["confidence"]),
                    similarity_score=similarity
                )

                scored_candidates.append({
                    "image_id": row["image_id"],
                    "url": row["url"],
                    "filename": row["filename"],
                    "subject": row["subject"],
                    "category": row["category"],
                    "caption": row["caption"],
                    "confidence": float(row["confidence"]),
                    "similarity_score": round(similarity, 4),
                    "guard_decision": decision,
                    "explanation": reason
                })

            # 5. Sort candidates: primary sort by similarity score descending
            scored_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

            # 6. Build suggestions and persist to DB
            # First, clean existing suggestions for this post
            conn.execute("DELETE FROM suggestions WHERE post_id = ?", (post_id,))

            suggestion_items: List[SuggestionItem] = []
            for rank_idx, item in enumerate(scored_candidates[:max_suggestions], start=1):
                suggestion_id = f"sug_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO suggestions (id, post_id, image_id, similarity_score, guard_decision, explanation, rank)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        suggestion_id,
                        post_id,
                        item["image_id"],
                        item["similarity_score"],
                        item["guard_decision"].value,
                        item["explanation"],
                        rank_idx
                    )
                )
                suggestion_items.append(
                    SuggestionItem(
                        id=suggestion_id,
                        image_id=item["image_id"],
                        image_url=item["url"],
                        image_caption=item["caption"],
                        image_subject=item["subject"],
                        image_category=item["category"],
                        confidence=item["confidence"],
                        similarity_score=item["similarity_score"],
                        guard_decision=item["guard_decision"],
                        explanation=item["explanation"],
                        rank=rank_idx
                    )
                )
            conn.commit()

            # 7. Determine overall match status
            # Top candidate must be ACCEPTED for MATCH_FOUND status
            top_rec = suggestion_items[0] if suggestion_items else None
            if top_rec and top_rec.guard_decision == GuardDecision.ACCEPTED:
                status = "MATCH_FOUND"
                overall_explanation = f"Recommended image '{top_rec.image_id}' with similarity {top_rec.similarity_score:.3f} ({top_rec.explanation})"
            else:
                status = "NO_CONFIDENT_MATCH"
                if top_rec:
                    overall_explanation = f"Top candidate '{top_rec.image_id}' rejected by safety guard: {top_rec.explanation}"
                else:
                    overall_explanation = "No indexed images available in the library to evaluate."

            return PostSuggestionsResponse(
                post_id=post_id,
                post_title=post_row["title"],
                status=status,
                top_recommendation=top_rec if (top_rec and top_rec.guard_decision == GuardDecision.ACCEPTED) else None,
                all_candidates=suggestion_items,
                explanation=overall_explanation
            )

matching_engine = MatchingEngine()
