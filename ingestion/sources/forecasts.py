"""
For demo, we generate a lightweight "consensus" forecast using yfinance analyst data.
If FMP key present, we can fetch richer data. This module is intentionally simple.
"""
from datetime import datetime, timedelta, timezone
import yfinance as yf
from loguru import logger
from ingestion.db import execute, fetchall
from ingestion.config import config


def fetch_analyst_targets(ticker: str) -> dict | None:
    """Get analyst price target + recommendation via yfinance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        target = info.get("targetMeanPrice")
        low = info.get("targetLowPrice")
        high = info.get("targetHighPrice")
        n = info.get("numberOfAnalystOpinions")
        if not target:
            return None
        now = datetime.now(timezone.utc)
        return {
            "ticker": ticker,
            "metric": "price",
            "horizon": "1Y",
            "target_value": float(target),
            "target_range_low": float(low) if low else None,
            "target_range_high": float(high) if high else None,
            "confidence": 0.65,  # placeholder for demo
            "method": "consensus",
            "source": f"{n or 'unknown'}_analysts",
            "source_url": None,
            "made_at": now,
            "valid_until": now + timedelta(days=365),
            "text_summary": (
                f"Consensus 1Y price target for {ticker}: ${target:.2f}"
                f" (range ${low or '?'}-${high or '?'}, n={n or '?'})"
            ),
        }
    except Exception as e:
        logger.error(f"Analyst target fetch failed {ticker}: {e}")
        return None


def store_forecast(fc: dict) -> bool:
    try:
        execute(
            """
            INSERT INTO forecasts
              (ticker, metric, horizon, target_value, target_range_low, target_range_high,
               confidence, method, source, source_url, made_at, valid_until, text_summary)
            VALUES
              (:ticker, :metric, :horizon, :target_value, :target_range_low, :target_range_high,
               :confidence, :method, :source, :source_url, :made_at, :valid_until, :text_summary)
            """,
            fc,
        )
        return True
    except Exception as e:
        logger.error(f"Forecast store failed: {e}")
        return False


def fetch_all_forecasts():
    total = 0
    for ticker in config.TICKERS:
        fc = fetch_analyst_targets(ticker)
        if fc and store_forecast(fc):
            total += 1
    logger.info(f"Forecasts: stored {total}")
    return total


def get_active_forecasts(ticker: str, limit: int = 10) -> list[dict]:
    return fetchall(
        """
        SELECT metric, horizon, target_value, target_range_low, target_range_high,
               confidence, method, source, made_at, valid_until
        FROM forecasts
        WHERE ticker = :t
          AND valid_until > NOW()
          AND realized_value IS NULL
        ORDER BY made_at DESC
        LIMIT :n
        """,
        {"t": ticker, "n": limit},
    )