# BUILDLOG.md — AI-Assisted Engineering Journal

**Author:** Jezreal Momoh  
**Project:** AI Image Understanding & Content Matching Engine (`flyrank-capstone-image-relevance`)  
**Track:** Backend AI Engineering — Week 8 Capstone  

---

## 1. Where AI Assisted & Accelerated Development
1. **Initial Corpus & Metadata Scaffolding**:
   - AI generated the initial 50-item JSON dataset across 5 categories (Wildlife, Landscapes, Technology, Architecture, Culinary), including attribution metadata conforming to Unsplash/Pexels free licenses.
2. **Schema & Contract Structuring**:
   - AI structured the Pydantic v2 `ImageTagSchema` and boundary error models to ensure input validation at HTTP boundaries.
3. **Pure-Python Vector Math Utilities**:
   - Accelerated the implementation of pure-Python vector cosine similarity and normalized Euclidean projection without needing C-extension dependencies.

---

## 2. Where AI Was Wrong, Hallucinated, or Required Architectural Intervention
1. **Mismatch Guard Evaluation Order Bug**:
   - *Issue:* Initially, the AI generated the Mismatch Guard with the similarity threshold gate evaluated before the taxonomic/category mismatch gate. When testing an adversarial candidate (`gray wolf` for a `red fox` article), the candidate had lower similarity than the 0.60 cutoff, returning `REJECTED_LOW_SIMILARITY` instead of detecting the category divergence.
   - *Fix:* Architected a priority-based gating sequence: confidence checks first, followed immediately by domain taxonomic incompatibility checks (`TAXONOMIC_CONSTRAINTS`). If a post explicitly asks for a `fox` and the candidate is a `wolf`, the guard flags `REJECTED_CATEGORY_MISMATCH` regardless of vector score.
2. **Strict Substring Matching in Evaluation Benchmark**:
   - *Issue:* The benchmark evaluation test for out-of-domain articles looked for `"below threshold"`, but the initial guard explanation returned `"below minimum similarity threshold"`.
   - *Fix:* Aligned the explanation template across the guard and evaluation suite to use clean, unambiguous diagnostic strings (`"is below threshold"`).
3. **Relative Database Path Drift**:
   - *Issue:* The AI wrote `data/image_engine.db` as a relative path, which caused `OperationalError: no such table` when commands were executed from workspace parent directories.
   - *Fix:* Replaced `DEFAULT_DB_PATH` with a dynamic anchor anchored to `PROJECT_ROOT / "data" / "image_engine.db"`.

---

## 3. Human Engineering Decisions & Invariants
1. **Zero-Dependency Vector Space**:
   - Rather than forcing heavy PyTorch/ChromaDB dependencies that exceed memory bounds or require native builds, designed an offline deterministic semantic encoder with 64 conceptual dimensions mapped to the corpus taxonomy, ensuring instant, reproducible test runs.
2. **Dual-Stream Embedding Storage**:
   - Separate embedding pipelines for post texts and image visual descriptions, persisted in SQLite with composite unique indexes `(entity_type, entity_id)` and WAL journaling for concurrent access.
3. **Fail-Closed AI Safety**:
   - Rather than returning a "best guess" image when similarity is weak, the engine enforces `status: NO_CONFIDENT_MATCH` with explicit rationale, treating model outputs as untrusted until proven valid.
