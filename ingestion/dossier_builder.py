"""
Builds a Dossier JSON per ticker (Contract A).
This is what Person 2 (RAG) and Person 3 (Agents) consume.
"""
import json
from datetime import datetime, timezone
from loguru import logger
from ingestion.db import fetchall, fetchone, execute
from ingestion.config import config
from ingestion.redis_client import set_json, get_json
from ingestion.sources.prices import get_latest_price, get_price_change
from ingestion.sources.news import get_recent_news
from ingestion.sources.filings import get_recent_filings
from ingestion.sources.forecasts import get_active_forecasts


COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "MCD": "McDonald's Corporation",
    "NVDA": "NVIDIA Corporation",
    "TSLA": "Tesla Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "KO": "The Coca-Cola Company",
    "XOM": "Exxon Mobil Corporation",
}


def _build_sources(news_items, filings, forecasts) -> list[dict]:
    sources = []
    idx = 1
    for n in news_items:
        sources.append({
            "id": idx,
            "name": n.get("source") or "Unknown",
            "date": str(n.get("event_time"))[:10],
            "url": n.get("url") or "",
        })
        idx += 1
    for f in filings:
        sources.append({
            "id": idx,
            "name": f"SEC {f.get('form_type')}",
            "date": str(f.get("filing_date")),
            "url": f.get("url") or "",
        })
        idx += 1
    for fc in forecasts:
        sources.append({
            "id": idx,
            "name": f"{fc.get('source')} ({fc.get('method')})",
            "date": str(fc.get("made_at"))[:10],
            "url": fc.get("source_url") or "",
        })
        idx += 1
    return sources


def _fundamentals(ticker: str) -> dict:
    row = fetchone(
        """
        SELECT pe, pe_5y_avg, peg, revenue_ttm, margin, debt_ebitda, market_cap, dividend_yield
        FROM fundamentals
        WHERE ticker = :t
        ORDER BY as_of DESC LIMIT 1
        """,
        {"t": ticker},
    )
    if not row:
        return {}
    return {k: (float(v) if v is not None else None) for k, v in row.items()}


def build_dossier(ticker: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    latest = get_latest_price(ticker) or {}
    change_1d = get_price_change(ticker, days=1)
    change_1m = get_price_change(ticker, days=30)

    news_items = get_recent_news(ticker, days=7, limit=10)
    filings = get_recent_filings(ticker, limit=5)
    forecasts = get_active_forecasts(ticker, limit=10)
    fundamentals = _fundamentals(ticker)

    sources = _build_sources(news_items, filings, forecasts)

    forecast_payload = [
        {
            "metric": f.get("metric"),
            "horizon": f.get("horizon"),
            "target": float(f["target_value"]) if f.get("target_value") is not None else None,
            "range": [
                float(f["target_range_low"]) if f.get("target_range_low") is not None else None,
                float(f["target_range_high"]) if f.get("target_range_high") is not None else None,
            ] if f.get("target_range_low") or f.get("target_range_high") else None,
            "confidence": float(f["confidence"]) if f.get("confidence") is not None else None,
            "method": f.get("method"),
            "source": f.get("source"),
            "made_at": str(f.get("made_at")),
            "valid_until": str(f.get("valid_until")),
            "source_accuracy": None,
            "n_historical": None,
        }
        for f in forecasts
    ]

    dossier = {
        "ticker": ticker,
        "name": COMPANY_NAMES.get(ticker, ticker),
        "as_of": now,
        "price": {
            "last": float(latest.get("close")) if latest.get("close") else None,
            "chg_1d": float(change_1d.get("change_pct", 0)) if change_1d else None,
            "chg_1m": float(change_1m.get("change_pct", 0)) if change_1m else None,
        },
        "fundamentals": fundamentals,
        "news_7d": [
            {
                "headline": n.get("headline"),
                "source": n.get("source"),
                "url": n.get("url"),
                "event_time": str(n.get("event_time")),
                "sentiment": float(n["sentiment"]) if n.get("sentiment") is not None else None,
            }
            for n in news_items
        ],
        "projects": [],
        "geopolitical": [],
        "risks": [],
        "catalysts": [],
        "forecasts": forecast_payload,
        "quant": {},
        "sources": sources,
    }

    execute(
        """
        INSERT INTO dossiers (ticker, as_of, payload, updated_at)
        VALUES (:t, :as_of, CAST(:payload AS jsonb), NOW())
        ON CONFLICT (ticker) DO UPDATE SET
          as_of = EXCLUDED.as_of,
          payload = EXCLUDED.payload,
          updated_at = NOW()
        """,
        {"t": ticker, "as_of": now, "payload": json.dumps(dossier, default=str)},
    )
    set_json(f"dossier:{ticker}", dossier, ttl_seconds=7200)
    return dossier


def build_all_dossiers() -> dict:
    results = {}
    for ticker in config.TICKERS:
        try:
            results[ticker] = build_dossier(ticker)
        except Exception as e:
            logger.error(f"Dossier failed {ticker}: {e}")
            results[ticker] = None
    logger.info(f"Dossiers built: {sum(1 for v in results.values() if v)}/{len(config.TICKERS)}")
    return results


def get_dossier(ticker: str) -> dict | None:
    """Fast path: cache → DB → rebuild."""
    cached = get_json(f"dossier:{ticker}")
    if cached:
        return cached
    row = fetchone("SELECT payload FROM dossiers WHERE ticker = :t", {"t": ticker})
    if row:
        return row["payload"]
    return build_dossier(ticker)


if __name__ == "__main__":
    d = build_dossier("MCD")
    print(json.dumps(d, indent=2, default=str))