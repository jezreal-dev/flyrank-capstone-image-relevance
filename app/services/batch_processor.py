"""Background batch processing system for asynchronous image ingestion and tagging."""
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from app.core.database import get_db_connection
from app.services.vision_service import vision_service
from app.services.embedding_service import embedding_service

CONFIDENCE_THRESHOLD = 0.70
MAX_RETRIES = 3

class BatchProcessor:
    def process_single_image(self, image_id: str, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
        """Processes a single image: vision tagging -> validation -> embedding -> storage.
        Includes exponential backoff retries.
        """
        with get_db_connection() as conn:
            row = conn.execute("SELECT id, url, filename FROM images WHERE id = ?", (image_id,)).fetchone()
            if not row:
                raise ValueError(f"Image '{image_id}' not found in database")
            url = row["url"]
            filename = row["filename"]

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # 1. Vision Tagging & Pydantic Schema Validation
                tags = vision_service.extract_structured_tags(image_id, url, filename)
                
                # Check low-confidence flag
                is_flagged = 1 if tags.confidence < CONFIDENCE_THRESHOLD else 0
                target_status = "flagged_for_review" if is_flagged else "completed"

                with get_db_connection() as conn:
                    # 2. Upsert Image Metadata (Idempotent)
                    conn.execute(
                        """
                        INSERT INTO image_metadata (image_id, subject, category, attributes_json, caption, confidence, is_flagged)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(image_id) DO UPDATE SET
                            subject = excluded.subject,
                            category = excluded.category,
                            attributes_json = excluded.attributes_json,
                            caption = excluded.caption,
                            confidence = excluded.confidence,
                            is_flagged = excluded.is_flagged,
                            created_at = CURRENT_TIMESTAMP
                        """,
                        (
                            image_id,
                            tags.subject,
                            tags.category,
                            json.dumps(tags.attributes),
                            tags.caption,
                            tags.confidence,
                            is_flagged
                        )
                    )

                    # Update parent image status
                    conn.execute(
                        "UPDATE images SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (target_status, image_id)
                    )
                    conn.commit()

                # 3. Generate and cache Image Embedding
                embedding_service.embed_and_store_image(
                    image_id=image_id,
                    subject=tags.subject,
                    category=tags.category,
                    caption=tags.caption,
                    attributes=tags.attributes
                )

                return {
                    "image_id": image_id,
                    "status": target_status,
                    "is_flagged": bool(is_flagged),
                    "confidence": tags.confidence,
                    "subject": tags.subject
                }

            except Exception as e:
                last_error = e
                time.sleep(0.05 * (2 ** (attempt - 1)))  # Exponential backoff

        # All retries exhausted
        with get_db_connection() as conn:
            conn.execute("UPDATE images SET status = 'failed' WHERE id = ?", (image_id,))
            conn.commit()
        raise RuntimeError(f"Failed processing image '{image_id}' after {max_retries} attempts: {last_error}")

    def run_batch_job(self, image_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Executes a complete batch ingestion job across images."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        with get_db_connection() as conn:
            if image_ids:
                placeholders = ",".join("?" for _ in image_ids)
                rows = conn.execute(f"SELECT id FROM images WHERE id IN ({placeholders})", image_ids).fetchall()
            else:
                rows = conn.execute("SELECT id FROM images WHERE status IN ('queued', 'failed')").fetchall()

            target_ids = [r["id"] for r in rows]
            total_items = len(target_ids)

            conn.execute(
                """
                INSERT INTO batch_jobs (id, job_type, status, total_items, processed_items, flagged_items, failed_items)
                VALUES (?, 'image_ingestion', 'running', ?, 0, 0, 0)
                """,
                (job_id, total_items)
            )
            conn.commit()

        processed = 0
        flagged = 0
        failed = 0

        for img_id in target_ids:
            try:
                res = self.process_single_image(img_id)
                processed += 1
                if res["is_flagged"]:
                    flagged += 1
            except Exception:
                failed += 1

            # Update batch job progress
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE batch_jobs 
                    SET processed_items = ?, flagged_items = ?, failed_items = ?
                    WHERE id = ?
                    """,
                    (processed, flagged, failed, job_id)
                )
                conn.commit()

        job_status = "completed" if failed == 0 else ("failed" if processed == 0 else "completed_with_errors")
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE batch_jobs 
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (job_status, job_id)
            )
            conn.commit()

        return {
            "job_id": job_id,
            "status": job_status,
            "total_items": total_items,
            "processed_items": processed,
            "flagged_items": flagged,
            "failed_items": failed
        }

batch_processor = BatchProcessor()
