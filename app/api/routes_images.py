"""API routes for image ingestion, batch processing, and catalog inspection."""
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from app.core.database import get_db_connection
from app.models.image_schema import (
    ImageCreateRequest,
    ImageResponse,
    BatchProcessRequest,
    BatchJobStatusResponse
)
from app.services.batch_processor import batch_processor

router = APIRouter(prefix="/api/images", tags=["images"])

@router.post("", response_model=ImageResponse, status_code=201)
def create_image(payload: ImageCreateRequest):
    """Boundary-validated image registration."""
    image_id = payload.id or f"img_{uuid.uuid4().hex[:10]}"
    with get_db_connection() as conn:
        existing = conn.execute("SELECT id FROM images WHERE id = ?", (image_id,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Image with ID '{image_id}' already exists")

        conn.execute(
            "INSERT INTO images (id, url, filename, status) VALUES (?, ?, ?, 'queued')",
            (image_id, payload.url, payload.filename)
        )
        conn.commit()

        # If pre-provided structured tags were attached, store immediately
        if payload.structured_tags:
            is_flagged = 1 if payload.structured_tags.confidence < 0.70 else 0
            conn.execute(
                """
                INSERT INTO image_metadata (image_id, subject, category, attributes_json, caption, confidence, is_flagged)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    payload.structured_tags.subject,
                    payload.structured_tags.category,
                    json.dumps(payload.structured_tags.attributes),
                    payload.structured_tags.caption,
                    payload.structured_tags.confidence,
                    is_flagged
                )
            )
            conn.execute(
                "UPDATE images SET status = ? WHERE id = ?",
                ("flagged_for_review" if is_flagged else "completed", image_id)
            )
            conn.commit()

    return get_image(image_id)

@router.get("", response_model=List[ImageResponse])
def list_images(
    status: Optional[str] = Query(None, description="Filter by status ('completed', 'flagged_for_review', 'queued')"),
    category: Optional[str] = Query(None, description="Filter by taxonomic category"),
    limit: int = Query(100, ge=1, le=200)
):
    with get_db_connection() as conn:
        query = """
            SELECT 
                img.id, img.url, img.filename, img.status, img.created_at,
                meta.subject, meta.category, meta.attributes_json, meta.caption, meta.confidence, meta.is_flagged
            FROM images img
            LEFT JOIN image_metadata meta ON img.id = meta.image_id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND img.status = ?"
            params.append(status)
        if category:
            query += " AND meta.category = ?"
            params.append(category)
        query += " ORDER BY img.created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            attrs = json.loads(r["attributes_json"]) if r["attributes_json"] else []
            result.append(
                ImageResponse(
                    id=r["id"],
                    url=r["url"],
                    filename=r["filename"],
                    status=r["status"],
                    subject=r["subject"],
                    category=r["category"],
                    attributes=attrs,
                    caption=r["caption"],
                    confidence=r["confidence"],
                    is_flagged=bool(r["is_flagged"]) if r["is_flagged"] is not None else False,
                    created_at=r["created_at"]
                )
            )
        return result

@router.get("/{image_id}", response_model=ImageResponse)
def get_image(image_id: str):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT 
                img.id, img.url, img.filename, img.status, img.created_at,
                meta.subject, meta.category, meta.attributes_json, meta.caption, meta.confidence, meta.is_flagged
            FROM images img
            LEFT JOIN image_metadata meta ON img.id = meta.image_id
            WHERE img.id = ?
            """,
            (image_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Image with ID '{image_id}' not found")

        attrs = json.loads(row["attributes_json"]) if row["attributes_json"] else []
        return ImageResponse(
            id=row["id"],
            url=row["url"],
            filename=row["filename"],
            status=row["status"],
            subject=row["subject"],
            category=row["category"],
            attributes=attrs,
            caption=row["caption"],
            confidence=row["confidence"],
            is_flagged=bool(row["is_flagged"]) if row["is_flagged"] is not None else False,
            created_at=row["created_at"]
        )

@router.post("/batch", response_model=BatchJobStatusResponse, status_code=202)
def trigger_batch_processing(payload: BatchProcessRequest, background_tasks: BackgroundTasks):
    """Triggers asynchronous batch processing off the request path."""
    job_res = batch_processor.run_batch_job(image_ids=payload.image_ids)
    return BatchJobStatusResponse(
        job_id=job_res["job_id"],
        status=job_res["status"],
        total_items=job_res["total_items"],
        processed_items=job_res["processed_items"],
        flagged_items=job_res["flagged_items"],
        failed_items=job_res["failed_items"]
    )
