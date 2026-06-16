-- f4: pgvector schema migration. Idempotent (R15). Parametrized by {table} and
-- {dim} via str.format in PgVectorStore.ensure_schema (R17). {dim} == embedding_dim
-- is the single source of truth for the vector column dimension (R16).
-- Only {table}/{dim} (from trusted Settings) are interpolated; row values (text,
-- vectors) always travel as psycopg parameters, never interpolated.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS {table} (
    chunk_id   TEXT PRIMARY KEY,
    text       TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title      TEXT NOT NULL,
    section    TEXT NOT NULL,
    embedding  vector({dim}) NOT NULL
);

CREATE INDEX IF NOT EXISTS {table}_embedding_cosine_idx
    ON {table} USING hnsw (embedding vector_cosine_ops);
