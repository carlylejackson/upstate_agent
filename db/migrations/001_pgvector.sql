-- Enable pgvector and migrate kb_chunks for vector similarity retrieval.
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE IF EXISTS kb_chunks
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Backfill from JSON embeddings if present (best-effort migration helper).
-- NOTE: run this with a script that parses JSON and updates vector values when needed.

CREATE INDEX IF NOT EXISTS kb_chunks_embedding_idx
  ON kb_chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

ANALYZE kb_chunks;
