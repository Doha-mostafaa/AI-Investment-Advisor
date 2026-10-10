import requests
import feedparser
from datetime import datetime, timedelta, timezone
from loguru import logger
from ingestion.db import execute, fetchall
from ingestion.config import config

NEWSAPI_URL = "https://newsapi.org/v2/everything"

RSS_FEEDS = {
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
}


def fetch_newsapi(ticker: str, days_back: int = 7, page_size: int = 20) -> list[dict]:
    if not config.NEWSAPI_KEY:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    try:
        r = requests.get(
            NEWSAPI_URL,
            params={
                "q": ticker,
                "from": since,
                "sortBy": "publishedAt",
                "pageSize": page_size,
                "language": "en",
                "apiKey": config.NEWSAPI_KEY,
            },
            timeout=10,
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [
            {
                "ticker": ticker,
                "headline": a.get("title", "")[:500],
                "summary": a.get("description", ""),
                "content": a.get("content", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "url": a.get("url", ""),
                "author": a.get("author", ""),
                "event_time": a.get("publishedAt"),
            }
            for a in articles if a.get("url")
        ]
    except Exception as e:
        logger.error(f"NewsAPI failed for {ticker}: {e}")
        return []


def fetch_rss_news() -> list[dict]:
    items = []
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                items.append({
                    "ticker": None,
                    "headline": entry.get("title", "")[:500],
                    "summary": entry.get("summary", "")[:1000],
                    "content": "",
                    "source": name,
                    "url": entry.get("link", ""),
                    "author": entry.get("author", ""),
                    "event_time": entry.get("published", datetime.now(timezone.utc).isoformat()),
                })
        except Exception as e:
            logger.error(f"RSS failed {name}: {e}")
    return items


def store_news(items: list[dict]) -> int:
    rows = 0
    for item in items:
        try:
            execute(
                """
                INSERT INTO news (ticker, headline, summary, content, source, url, author, event_time)
                VALUES (:ticker, :headline, :summary, :content, :source, :url, :author, :event_time)
                """,
                item,
            )
            rows += 1
        except Exception as e:
            logger.debug(f"News insert skipped: {e}")
    return rows


def fetch_all_news():
    total = 0
    for ticker in config.TICKERS:
        items = fetch_newsapi(ticker)
        total += store_news(items)
    total += store_news(fetch_rss_news())
    logger.info(f"News: stored {total} items")
    return total


def get_recent_news(ticker: str, days: int = 7, limit: int = 10) -> list[dict]:
    return fetchall(
        """
        SELECT headline, source, url, event_time, sentiment, summary
        FROM news
        WHERE ticker = :t
          AND event_time > NOW() - INTERVAL '1 day' * :d
        ORDER BY event_time DESC
        LIMIT :n
        """,
        {"t": ticker, "d": days, "n": limit},
    )