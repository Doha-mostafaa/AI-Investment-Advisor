"""
check_data.py - Quick health check for Person 1's data (Postgres + Redis).

Put this file next to docker-compose.yml and .env, then run:
    pip install psycopg2-binary python-dotenv redis
    python check_data.py

It does NOT change anything. It only reads.
"""
import os
import sys

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

load_dotenv()

EXPECTED = ["AAPL", "MSFT", "GOOGL", "AMZN", "MCD", "NVDA", "TSLA", "JPM", "KO", "XOM"]
TICKER_COLS = ("ticker", "symbol")
TIME_COLS = ("event_time", "ingest_time", "created_at", "date", "timestamp",
             "published_at", "made_at", "valid_until")

issues = {"fail": 0, "warn": 0}


def ok(msg):
    print(f"✅ {msg}")


def warn(msg):
    issues["warn"] += 1
    print(f"⚠️  {msg}")


def bad(msg):
    issues["fail"] += 1
    print(f"❌ {msg}")


def title(msg):
    print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}")


def short(v, n=80):
    s = str(v).replace("\n", " ")
    return s if len(s) <= n else s[:n] + "..."


# ---------------------------------------------------------------- Postgres
def connect():
    user = os.getenv("POSTGRES_USER")
    pw = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    # Running on your laptop: Docker maps container port 5432 -> 5433 on localhost
    candidates = [
        (os.getenv("POSTGRES_HOST", "localhost"), os.getenv("POSTGRES_PORT", "5433")),
        ("localhost", "5433"),
        ("localhost", "5432"),
    ]
    tried = set()
    for host, port in candidates:
        if (host, port) in tried:
            continue
        tried.add((host, port))
        try:
            conn = psycopg2.connect(host=host, port=port, dbname=db, user=user,
                                    password=pw, connect_timeout=5)
            ok(f"Connected to Postgres at {host}:{port}")
            return conn
        except Exception as e:
            warn(f"Could not connect at {host}:{port} -> {short(e, 100)}")
    bad("Postgres connection failed. Is `docker compose up -d` running? Is .env correct?")
    sys.exit(1)


def check_postgres():
    title("1) POSTGRES")
    conn = connect()
    cur = conn.cursor()

    # pgvector
    cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    available = cur.fetchone() is not None
    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    installed = cur.fetchone() is not None
    if installed:
        ok("pgvector is installed")
    elif available:
        warn("pgvector available but not enabled -> run: CREATE EXTENSION vector;")
    else:
        bad("pgvector NOT available -> change image to pgvector/pgvector:pg16")

    # tables
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = [r[0] for r in cur.fetchall()]
    if not tables:
        bad("No tables found in the public schema (schema/migrations not applied?)")
        return
    ok(f"Found {len(tables)} tables: {', '.join(tables)}")

    for t in tables:
        title(f"TABLE: {t}")
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (t,))
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        print("Columns:", ", ".join(f"{n} ({d})" for n, d in cols))

        cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(t)))
        n = cur.fetchone()[0]
        if n == 0:
            bad(f"{t}: EMPTY (0 rows)")
            continue
        ok(f"{t}: {n} rows")

        # sample rows
        cur.execute(sql.SQL("SELECT * FROM {} LIMIT 2").format(sql.Identifier(t)))
        for row in cur.fetchall():
            print("  sample:", {c: short(v) for c, v in zip(col_names, row)})

        # ticker coverage
        for tc in TICKER_COLS:
            if tc in col_names:
                cur.execute(sql.SQL("SELECT {c}, count(*) FROM {t} GROUP BY {c}")
                            .format(c=sql.Identifier(tc), t=sql.Identifier(t)))
                found = {str(r[0]).upper(): r[1] for r in cur.fetchall()}
                missing = [x for x in EXPECTED if x not in found]
                if missing:
                    warn(f"{t}: missing tickers -> {', '.join(missing)}")
                else:
                    ok(f"{t}: all 10 tickers present")
                print("  per ticker:", found)
                break

        # time range / freshness
        for tm in TIME_COLS:
            if tm in col_names:
                cur.execute(sql.SQL("SELECT min({c}), max({c}) FROM {t}")
                            .format(c=sql.Identifier(tm), t=sql.Identifier(t)))
                lo, hi = cur.fetchone()
                print(f"  {tm}: from {lo} to {hi}")

    conn.close()


# ------------------------------------------------------------------- Redis
def check_redis():
    title("2) REDIS")
    try:
        import redis
    except ImportError:
        warn("redis package not installed -> pip install redis")
        return
    host = os.getenv("REDIS_HOST", "localhost")
    if host in ("redis",):  # docker service name doesn't resolve from your laptop
        host = "localhost"
    port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        r = redis.Redis(host=host, port=port, socket_connect_timeout=5, decode_responses=True)
        r.ping()
        ok(f"Connected to Redis at {host}:{port}")
        keys = list(r.scan_iter("*", count=100))
        if keys:
            ok(f"{len(keys)} keys in cache, e.g. {keys[:10]}")
        else:
            warn("Redis is empty (no cached dossiers yet)")
    except Exception as e:
        bad(f"Redis check failed: {short(e, 120)}")


if __name__ == "__main__":
    check_postgres()
    check_redis()
    title("SUMMARY")
    print(f"❌ failures: {issues['fail']}   ⚠️  warnings: {issues['warn']}")
    print("Copy ALL of this output and send it to Claude.")
