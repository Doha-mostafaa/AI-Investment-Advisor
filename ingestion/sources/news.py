<<<<<<< HEAD
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
=======
"""
news.py (improved) - drop-in replacement for ingestion/sources/news.py

What changed vs. the original:
  1. Every article is tagged with a ticker (per-ticker feeds, or entity_resolution for general feeds).
  2. Free per-ticker sources added: Yahoo Finance RSS + Google News RSS (no API key needed).
  3. Dead Reuters feed removed.
  4. No duplicate rows when you run it twice (checks url + ticker first).
  5. HTML stripped from summaries; dates normalised to ISO.
All original function names/signatures are kept, so dossier_builder etc. keep working.
"""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
import requests
from bs4 import BeautifulSoup
from loguru import logger

from ingestion.config import config
from ingestion.db import execute, fetchall, fetchone
from ingestion.entity_resolution import ALIASES, resolve

NEWSAPI_URL = "https://newsapi.org/v2/everything"
UA = "Mozilla/5.0 (compatible; StockResearchDemo/1.0)"

# General (market-wide) feeds. Tickers are detected from the text.
RSS_FEEDS = {
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "cnbc_markets": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
}

MAX_PER_FEED = 15


# ----------------------------------------------------------------- helpers
def _clean(text: str, limit: int = 1000) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)[:limit]


def _iso(value) -> str:
    """Turn many date formats into an ISO string (fallback: now)."""
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(str(value)).astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _parse_feed(url: str):
    return feedparser.parse(url, agent=UA)


def _entry_to_item(entry, ticker, source_name: str) -> dict:
    source = source_name
    src = entry.get("source")
    if isinstance(src, dict) and src.get("title"):
        source = src["title"]
    return {
        "ticker": ticker,
        "headline": _clean(entry.get("title", ""), 500),
        "summary": _clean(entry.get("summary", ""), 1000),
        "content": "",
        "source": source,
        "url": entry.get("link", ""),
        "author": entry.get("author", ""),
        "event_time": _iso(entry.get("published") or entry.get("updated")),
    }


# ----------------------------------------------------------------- sources
def fetch_newsapi(ticker: str, days_back: int = 7, page_size: int = 20) -> list[dict]:
    if not config.NEWSAPI_KEY:
        return []
    name = ALIASES.get(ticker, [ticker])[0]
>>>>>>> 469c16d (Clean initial commit)
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    try:
        r = requests.get(
            NEWSAPI_URL,
            params={
<<<<<<< HEAD
                "q": ticker,
=======
                "q": f"{name} stock",
>>>>>>> 469c16d (Clean initial commit)
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
<<<<<<< HEAD
                "headline": a.get("title", "")[:500],
                "summary": a.get("description", ""),
                "content": a.get("content", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "url": a.get("url", ""),
                "author": a.get("author", ""),
=======
                "headline": (a.get("title") or "")[:500],
                "summary": a.get("description") or "",
                "content": a.get("content") or "",
                "source": (a.get("source") or {}).get("name", ""),
                "url": a.get("url", ""),
                "author": a.get("author") or "",
>>>>>>> 469c16d (Clean initial commit)
                "event_time": a.get("publishedAt"),
            }
            for a in articles if a.get("url")
        ]
    except Exception as e:
<<<<<<< HEAD
        logger.error(f"NewsAPI failed for {ticker}: {e}")
=======
        logger.error(f"NewsAPI failed for {ticker}: {type(e).__name__}")
        return []


def fetch_yahoo_rss(ticker: str) -> list[dict]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    try:
        feed = _parse_feed(url)
        return [_entry_to_item(e, ticker, "yahoo_finance") for e in feed.entries[:MAX_PER_FEED]]
    except Exception as e:
        logger.error(f"Yahoo RSS failed for {ticker}: {e}")
        return []


def fetch_google_news(ticker: str) -> list[dict]:
    name = ALIASES.get(ticker, [ticker])[0]
    q = quote(f"{name} stock when:7d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = _parse_feed(url)
        return [_entry_to_item(e, ticker, "google_news") for e in feed.entries[:MAX_PER_FEED]]
    except Exception as e:
        logger.error(f"Google News failed for {ticker}: {e}")
>>>>>>> 469c16d (Clean initial commit)
        return []


def fetch_rss_news() -> list[dict]:
<<<<<<< HEAD
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
=======
    """General feeds: detect which tickers each article mentions."""
    items = []
    for name, url in RSS_FEEDS.items():
        try:
            feed = _parse_feed(url)
            for entry in feed.entries[:20]:
                base = _entry_to_item(entry, None, name)
                tickers = resolve(f"{base['headline']} {base['summary']}")
                if tickers:
                    for t in tickers:  # one row per mentioned ticker
                        items.append({**base, "ticker": t})
                else:
                    items.append(base)  # market-wide news (ticker stays NULL)
>>>>>>> 469c16d (Clean initial commit)
        except Exception as e:
            logger.error(f"RSS failed {name}: {e}")
    return items


<<<<<<< HEAD
def store_news(items: list[dict]) -> int:
    rows = 0
    for item in items:
        try:
=======
# ----------------------------------------------------------------- storage
def store_news(items: list[dict]) -> int:
    rows = 0
    for item in items:
        if not item.get("url") or not item.get("headline"):
            continue
        try:
            exists = fetchone(
                "SELECT 1 AS x FROM news WHERE url = :u AND ticker IS NOT DISTINCT FROM :t",
                {"u": item["url"], "t": item.get("ticker")},
            )
            if exists:
                continue
>>>>>>> 469c16d (Clean initial commit)
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
<<<<<<< HEAD
        items = fetch_newsapi(ticker)
        total += store_news(items)
    total += store_news(fetch_rss_news())
=======
        n_api = store_news(fetch_newsapi(ticker))
        n_yh = store_news(fetch_yahoo_rss(ticker))
        n_gn = store_news(fetch_google_news(ticker))
        logger.info(f"{ticker}: newsapi={n_api} yahoo={n_yh} google={n_gn}")
        total += n_api + n_yh + n_gn
    n_rss = store_news(fetch_rss_news())
    logger.info(f"General RSS: {n_rss}")
    total += n_rss
>>>>>>> 469c16d (Clean initial commit)
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
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 469c16d (Clean initial commit)
