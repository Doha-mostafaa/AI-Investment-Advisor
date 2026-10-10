"""
fill_fundamentals.py - Fill the empty `fundamentals` table using yfinance.

Put it in the project ROOT (next to run_ingestion.py), then run:
    python fill_fundamentals.py
    python run_ingestion.py dossiers      # rebuild dossiers so they include fundamentals
"""
import datetime as dt
import math
import os

import psycopg2
import yfinance as yf
from dotenv import load_dotenv
from psycopg2.extras import Json

load_dotenv()

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "MCD", "NVDA", "TSLA", "JPM", "KO", "XOM"]


def num(v):
    """Return a clean float or None (yfinance sometimes gives None, NaN, inf or strings)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def connect():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    if host in ("postgres", ""):
        host = "localhost"
    if port == "5432":
        port = "5433"
    return psycopg2.connect(
        host=host, port=port,
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        connect_timeout=5,
    )


def main():
    conn = connect()
    cur = conn.cursor()
    today = dt.date.today()
    now = dt.datetime.now(dt.timezone.utc)
    saved = 0

    for t in TICKERS:
        try:
            info = yf.Ticker(t).info or {}
        except Exception as e:
            print(f"❌ {t}: {type(e).__name__}: {str(e)[:100]}")
            continue

        total_debt, ebitda = num(info.get("totalDebt")), num(info.get("ebitda"))
        debt_ebitda = (total_debt / ebitda) if (total_debt is not None and ebitda and ebitda > 0) else None

        row = {
            "pe": num(info.get("trailingPE")),
            "pe_5y_avg": None,  # not available from yfinance
            "peg": num(info.get("pegRatio") or info.get("trailingPegRatio")),
            "revenue_ttm": num(info.get("totalRevenue")),
            "margin": num(info.get("profitMargins")),
            "debt_ebitda": debt_ebitda,
            "market_cap": num(info.get("marketCap")),
            "dividend_yield": num(info.get("dividendYield")),
        }
        raw = {k: num(info.get(k)) for k in
               ("trailingPE", "forwardPE", "pegRatio", "totalRevenue", "profitMargins",
                "totalDebt", "ebitda", "marketCap", "dividendYield", "beta")}

        if all(v is None for v in row.values()):
            print(f"⚠️  {t}: no fundamentals returned")
            continue

        cur.execute("""
            INSERT INTO fundamentals
                (ticker, as_of, pe, pe_5y_avg, peg, revenue_ttm, margin,
                 debt_ebitda, market_cap, dividend_yield, raw, event_time)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (ticker, as_of) DO UPDATE SET
                pe=EXCLUDED.pe, peg=EXCLUDED.peg, revenue_ttm=EXCLUDED.revenue_ttm,
                margin=EXCLUDED.margin, debt_ebitda=EXCLUDED.debt_ebitda,
                market_cap=EXCLUDED.market_cap, dividend_yield=EXCLUDED.dividend_yield,
                raw=EXCLUDED.raw, ingest_time=NOW()
        """, (t, today, row["pe"], row["pe_5y_avg"], row["peg"], row["revenue_ttm"],
              row["margin"], row["debt_ebitda"], row["market_cap"], row["dividend_yield"],
              Json(raw), now))
        conn.commit()
        saved += 1
        print(f"✅ {t}: PE={row['pe']}  margin={row['margin']}  mcap={row['market_cap']}")

    conn.close()
    print(f"\nSaved {saved}/{len(TICKERS)} tickers. Now run: python run_ingestion.py dossiers")


if __name__ == "__main__":
    main()
