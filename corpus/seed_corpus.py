"""Corpus seeding and initialization script.
Populates SQLite with ~50 images and seed posts, then triggers batch ingestion.
"""
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import init_db, get_db_connection
from app.services.batch_processor import batch_processor

def seed_database():
    print("[1/4] Initializing database tables and indexes...")
    init_db()

    dataset_path = PROJECT_ROOT / "corpus" / "dataset.json"
    with open(dataset_path, "r") as f:
        images = json.load(f)

    print(f"[2/4] Seeding {len(images)} images into library...")
    with get_db_connection() as conn:
        for img in images:
            conn.execute(
                """
                INSERT INTO images (id, url, filename, status)
                VALUES (?, ?, ?, 'queued')
                ON CONFLICT(id) DO UPDATE SET
                    url = excluded.url,
                    filename = excluded.filename
                """,
                (img["id"], img["url"], img["filename"])
            )
        conn.commit()

    print("[3/4] Running batch processing job across all images (vision tagging + embeddings)...")
    batch_result = batch_processor.run_batch_job([img["id"] for img in images])
    print(f"      Batch complete: {batch_result['processed_items']}/{batch_result['total_items']} processed, "
          f"{batch_result['flagged_items']} flagged for low confidence, {batch_result['failed_items']} failed.")

    print("[4/4] Seeding canonical editorial articles for acceptance probes...")
    sample_posts = [
        {
            "id": "post_fox_01",
            "title": "The Behavior and Ecology of the Red Fox",
            "slug": "the-behavior-and-ecology-of-the-red-fox",
            "content": "A scientific study observing the hunting strategies, denning patterns, and autumn foliage camouflage of the wild red fox (Vulpes vulpes) in temperate woodlands.",
            "target_subject": "red fox"
        },
        {
            "id": "post_wolf_01",
            "title": "The Social Pack Dynamics of Gray Wolves",
            "slug": "the-social-pack-dynamics-of-gray-wolves",
            "content": "Detailed wildlife observation of Canis lupus in freezing winter tundras, focusing on pack hierarchy and endurance hunting in deep snow.",
            "target_subject": "gray wolf"
        },
        {
            "id": "post_dog_01",
            "title": "Puppy Training and Domestic Canine Companionship",
            "slug": "puppy-training-and-domestic-canine-companionship",
            "content": "Practical advice for training your golden retriever or family pet in municipal parks with positive reinforcement and leash etiquette.",
            "target_subject": "domestic dog"
        },
        {
            "id": "post_code_01",
            "title": "Clean Code Architecture for Python Web Services",
            "slug": "clean-code-architecture-for-python-web-services",
            "content": "Designing high-throughput backend APIs using typed Python, dependency injection, and clean boundaries between HTTP routes and database persistence.",
            "target_subject": "software code editor"
        },
        {
            "id": "post_unmatched_01",
            "title": "Quantum Entanglement and Cryogenic Superconducting Circuits",
            "slug": "quantum-entanglement-and-cryogenic-superconducting-circuits",
            "content": "Exploring topological qubit phase transitions and non-Abelian anyon braiding inside sub-kelvin dilution refrigerators for quantum computational acceleration.",
            "target_subject": "quantum physics"
        }
    ]

    with get_db_connection() as conn:
        for post in sample_posts:
            conn.execute(
                """
                INSERT INTO posts (id, title, slug, content, target_subject, status)
                VALUES (?, ?, ?, ?, ?, 'published')
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    slug = excluded.slug,
                    content = excluded.content,
                    target_subject = excluded.target_subject
                """,
                (post["id"], post["title"], post["slug"], post["content"], post["target_subject"])
            )
        conn.commit()

    print("Corpus seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
