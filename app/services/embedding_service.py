"""Dual-stream embedding generation service for image metadata and post content."""
import json
import time
from typing import List, Dict, Any
from app.core.vector_math import generate_semantic_vector, VECTOR_DIMENSIONS
from app.core.cost_tracker import tracker
from app.core.database import get_db_connection

class EmbeddingService:
    def __init__(self, provider: str = "offline"):
        self.provider = provider
        self.dimensions = VECTOR_DIMENSIONS

    def embed_text(self, text: str, entity_type: str) -> List[float]:
        start_time = time.time()
        vector = generate_semantic_vector(text)
        latency_ms = (time.time() - start_time) * 1000.0

        # Track tokens & attribution
        tokens = max(1, len(text.split()))
        tracker.record_call(
            operation="embedding_generation",
            model_name="text-embedding-004" if self.provider == "gemini" else "offline-semantic-embedder",
            input_tokens=tokens,
            output_tokens=0,
            latency_ms=round(latency_ms, 2),
            is_free_tier=True
        )
        return vector

    def store_embedding(self, entity_type: str, entity_id: str, vector: List[float]):
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO embeddings (entity_type, entity_id, vector_json, dimensions)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    vector_json = excluded.vector_json,
                    dimensions = excluded.dimensions,
                    created_at = CURRENT_TIMESTAMP
                """,
                (entity_type, entity_id, json.dumps(vector), len(vector))
            )
            conn.commit()

    def get_embedding(self, entity_type: str, entity_id: str) -> List[float] | None:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT vector_json FROM embeddings WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            ).fetchone()
            if row:
                return json.loads(row["vector_json"])
            return None

    def embed_and_store_image(self, image_id: str, subject: str, category: str, caption: str, attributes: List[str]):
        composite_text = f"{subject} {category} {caption} {' '.join(attributes)}"
        vector = self.embed_text(composite_text, entity_type="image")
        self.store_embedding("image", image_id, vector)
        return vector

    def embed_and_store_post(self, post_id: str, title: str, content: str, target_subject: str | None = None):
        composite_text = f"{title} {content} {target_subject or ''}"
        vector = self.embed_text(composite_text, entity_type="post")
        self.store_embedding("post", post_id, vector)
        return vector

embedding_service = EmbeddingService()
