"""
rag_index.py - Person 2's first working RAG slice.

  1) Creates the `documents` table (pgvector).
  2) Embeds news + filings that are not embedded yet (free model, runs on CPU).
  3) retrieve_facts(ticker, query, top_k) = hybrid search (vector + BM25, fused with RRF).

Put it in the project ROOT, then:
    pip install sentence-transformers rank_bm25
    python rag_index.py build                      # embed everything (first run downloads the model)
    python rag_index.py ask NVDA "latest news about GPUs"
"""
import os
import re
import sys

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384 dims, fast on CPU
DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts, is_query=False):
    if is_query:
        texts = [QUERY_PREFIX + t for t in texts]
    return get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def vec_literal(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def connect():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    if host in ("postgres", ""):
        host = "localhost"
    if port == "5432":
        port = "5433"
    return psycopg2.connect(host=host, port=port, dbname=os.getenv("POSTGRES_DB"),
                            user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"))


SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_id BIGINT NOT NULL,
    ticker TEXT,
    text TEXT NOT NULL,
    url TEXT,
    source TEXT,
    event_time TIMESTAMPTZ,
    embedding vector({DIM}),
    UNIQUE (source_table, source_id)
);
CREATE INDEX IF NOT EXISTS idx_documents_ticker ON documents (ticker);
"""


# ------------------------------------------------------------------ build
def build_index(batch=64):
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(SCHEMA)
    conn.commit()

    cur.execute("""
        SELECT 'news' AS source_table, id AS source_id, ticker,
               trim(coalesce(headline,'') || '. ' || coalesce(summary,'')) AS text,
               url, source, event_time
        FROM news
        WHERE ticker IS NOT NULL
        UNION ALL
        SELECT 'filings', id, ticker,
               ticker || ' ' || form_type || ' filing dated ' || filing_date::text
                   || coalesce('. ' || title, '') || coalesce('. ' || left(content, 2000), ''),
               url, 'SEC EDGAR', event_time
        FROM filings
    """)
    candidates = cur.fetchall()

    cur.execute("SELECT source_table, source_id FROM documents")
    done = {(r["source_table"], r["source_id"]) for r in cur.fetchall()}
    todo = [c for c in candidates if (c["source_table"], c["source_id"]) not in done and c["text"]]
    print(f"{len(candidates)} candidates, {len(todo)} new to embed")

    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        vecs = embed([c["text"] for c in chunk])
        for c, v in zip(chunk, vecs):
            cur.execute("""
                INSERT INTO documents (source_table, source_id, ticker, text, url, source, event_time, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)
                ON CONFLICT (source_table, source_id) DO NOTHING
            """, (c["source_table"], c["source_id"], c["ticker"], c["text"], c["url"],
                  c["source"], c["event_time"], vec_literal(v)))
        conn.commit()
        print(f"  embedded {min(i + batch, len(todo))}/{len(todo)}")
    conn.close()
    print("Done.")


# --------------------------------------------------------------- retrieve
def _tok(s):
    return re.findall(r"[a-z0-9']+", s.lower())


def retrieve_facts(ticker: str, query: str, top_k: int = 5, pool: int = 20) -> list[dict]:
    """Hybrid retrieval. Every result carries a source_id like 'news:123' for citations."""
    from rank_bm25 import BM25Okapi

    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # vector ranking
    qv = vec_literal(embed([query], is_query=True)[0])
    cur.execute("""
        SELECT id, source_table, source_id, text, url, source, event_time, ticker,
               1 - (embedding <=> %s::vector) AS score
        FROM documents WHERE ticker = %s
        ORDER BY embedding <=> %s::vector LIMIT %s
    """, (qv, ticker, qv, pool))
    vec_rows = cur.fetchall()

    # keyword ranking (BM25 over this ticker's docs - small, so this is cheap)
    cur.execute("SELECT id, source_table, source_id, text, url, source, event_time, ticker "
                "FROM documents WHERE ticker = %s", (ticker,))
    all_rows = cur.fetchall()
    conn.close()
    if not all_rows:
        return []  # no news -> empty list, never crash

    bm25 = BM25Okapi([_tok(r["text"]) for r in all_rows])
    scores = bm25.get_scores(_tok(query))
    bm_rows = [r for _, r in sorted(zip(scores, all_rows), key=lambda x: -x[0])[:pool]]

    # Reciprocal Rank Fusion
    fused, by_id = {}, {}
    for rows in (vec_rows, bm_rows):
        for rank, r in enumerate(rows):
            fused[r["id"]] = fused.get(r["id"], 0.0) + 1.0 / (60 + rank)
            by_id[r["id"]] = r
    best = sorted(fused, key=fused.get, reverse=True)[:top_k]

    out = []
    for doc_id in best:
        r = by_id[doc_id]
        out.append({
            "source_id": f"{r['source_table']}:{r['source_id']}",
            "ticker": r["ticker"],
            "text": r["text"],
            "url": r["url"],
            "source": r["source"],
            "event_time": r["event_time"].isoformat() if r["event_time"] else None,
            "score": round(fused[doc_id], 4),
        })
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        build_index()
    elif len(sys.argv) >= 4 and sys.argv[1] == "ask":
        for hit in retrieve_facts(sys.argv[2].upper(), " ".join(sys.argv[3:])):
            print(f"[{hit['source_id']}] ({hit['source']}, {hit['event_time']})\n  {hit['text'][:200]}\n  {hit['url']}\n")
    else:
        print(__doc__)
