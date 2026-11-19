"""API routes for editorial posts and Mismatch-Guarded image suggestions."""
import uuid
import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.core.database import get_db_connection
from app.models.post_schema import PostCreateRequest, PostResponse
from app.models.matching_schema import PostSuggestionsResponse
from app.services.matching_engine import matching_engine

router = APIRouter(prefix="/api/posts", tags=["posts"])

def slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned)

@router.post("", response_model=PostResponse, status_code=201)
def create_post(payload: PostCreateRequest):
    post_id = payload.id or f"post_{uuid.uuid4().hex[:10]}"
    base_slug = payload.slug or slugify(payload.title)

    with get_db_connection() as conn:
        slug = base_slug
        suffix = 1
        while conn.execute("SELECT id FROM posts WHERE slug = ?", (slug,)).fetchone():
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        conn.execute(
            """
            INSERT INTO posts (id, title, slug, content, target_subject, status)
            VALUES (?, ?, ?, ?, ?, 'published')
            """,
            (post_id, payload.title, slug, payload.content, payload.target_subject)
        )
        conn.commit()

        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return PostResponse(**dict(row))

@router.get("", response_model=List[PostResponse])
def list_posts(limit: int = Query(50, ge=1, le=100)):
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [PostResponse(**dict(r)) for r in rows]

@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: str):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Post with ID '{post_id}' not found")
        return PostResponse(**dict(row))

@router.get("/{post_id}/suggestions", response_model=PostSuggestionsResponse)
def get_post_image_suggestions(
    post_id: str,
    max_suggestions: int = Query(5, ge=1, le=10)
):
    """Core Matching & Mismatch Guard endpoint:
    Returns ranked image suggestions or refuses with diagnostic reasons.
    """
    try:
        response = matching_engine.rank_and_guard_candidates(
            post_id=post_id,
            max_suggestions=max_suggestions
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
