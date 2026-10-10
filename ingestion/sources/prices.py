import yfinance as yf
from datetime import datetime, timezone
from loguru import logger
from ingestion.db import execute, fetchone, fetchall
from ingestion.config import config


def fetch_and_store_prices(ticker: str, days_back: int = 30):
    """Fetch daily OHLCV from yfinance and upsert into prices table."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=f"{days_back}d", interval="1d")
        if df.empty:
            logger.warning(f"No price data for {ticker}")
            return 0

        rows = 0
        for ts, row in df.iterrows():
            ts_utc = ts.tz_convert("UTC").to_pydatetime()
            execute(
                """
                INSERT INTO prices (ticker, ts, open, high, low, close, volume, event_time, source)
                VALUES (:ticker, :ts, :open, :high, :low, :close, :volume, :event_time, :source)
                ON CONFLICT (ticker, ts) DO UPDATE SET
                  close = EXCLUDED.close,
                  volume = EXCLUDED.volume
                """,
                {
                    "ticker": ticker,
                    "ts": ts_utc,
                    "open": float(row["Open"]) if row["Open"] else None,
                    "high": float(row["High"]) if row["High"] else None,
                    "low": float(row["Low"]) if row["Low"] else None,
                    "close": float(row["Close"]) if row["Close"] else None,
                    "volume": int(row["Volume"]) if row["Volume"] else None,
                    "event_time": ts_utc,
                    "source": "yfinance",
                },
            )
            rows += 1
        logger.info(f"Prices: {ticker} stored {rows} rows")
        return rows
    except Exception as e:
        logger.error(f"Price fetch failed for {ticker}: {e}")
        return 0


def fetch_all_prices():
    total = 0
    for ticker in config.TICKERS:
        total += fetch_and_store_prices(ticker)
    return total


def get_latest_price(ticker: str) -> dict:
    row = fetchone(
        """
        SELECT close, ts FROM prices
        WHERE ticker = :t
        ORDER BY ts DESC LIMIT 1
        """,
        {"t": ticker},
    )
    return row or {}


def get_price_change(ticker: str, days: int = 1) -> dict:
    rows = fetchall(
        """
        SELECT close, ts FROM prices
        WHERE ticker = :t
        ORDER BY ts DESC LIMIT :n
        """,
        {"t": ticker, "n": days + 1},
    )
    if len(rows) < 2:
        return {}
    latest = rows[0]["close"]
    prev = rows[-1]["close"]
    if not latest or not prev:
        return {}
    return {
        "last": float(latest),
        "change": float(latest - prev),
        "change_pct": float((latest - prev) / prev * 100),
    }