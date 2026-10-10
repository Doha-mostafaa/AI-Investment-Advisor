import requests
from loguru import logger
from ingestion.db import execute, fetchall
from ingestion.config import config

SEC_BASE = "https://data.sec.gov"

TICKER_TO_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "MCD":  "0000063908",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "JPM":  "0000019617",
    "KO":   "0000021344",
    "XOM":  "0000034088",
}

HEADERS = {
    "User-Agent": config.SEC_USER_AGENT,
    "Accept": "application/json",
}


def fetch_filings_for_ticker(ticker: str, forms: list[str] = None) -> list[dict]:
    forms = forms or ["10-K", "10-Q", "8-K"]
    cik = TICKER_TO_CIK.get(ticker)
    if not cik:
        return []
    try:
        r = requests.get(f"{SEC_BASE}/submissions/CIK{cik}.json", headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        recent = data.get("filings", {}).get("recent", {})
        results = []
        for i, form in enumerate(recent.get("form", [])):
            if form not in forms:
                continue
            accession = recent["accessionNumber"][i].replace("-", "")
            filing_date = recent["filingDate"][i]
            primary_doc = recent["primaryDocument"][i]
            url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{primary_doc}"
            results.append({
                "ticker": ticker,
                "form_type": form,
                "filing_date": filing_date,
                "accession_no": recent["accessionNumber"][i],
                "title": recent.get("primaryDocDescription", [""])[i] if i < len(recent.get("primaryDocDescription", [])) else "",
                "url": url,
                "content": None,
                "event_time": f"{filing_date}T00:00:00+00:00",
            })
            if len(results) >= 10:
                break
        return results
    except Exception as e:
        logger.error(f"SEC fetch failed for {ticker}: {e}")
        return []


def store_filings(items: list[dict]) -> int:
    rows = 0
    for item in items:
        try:
            execute(
                """
                INSERT INTO filings (ticker, form_type, filing_date, accession_no, title, url, content, event_time)
                VALUES (:ticker, :form_type, :filing_date, :accession_no, :title, :url, :content, :event_time)
                ON CONFLICT (accession_no) DO NOTHING
                """,
                item,
            )
            rows += 1
        except Exception as e:
            logger.debug(f"Filing skip: {e}")
    return rows


def fetch_all_filings():
    total = 0
    for ticker in config.TICKERS:
        items = fetch_filings_for_ticker(ticker)
        total += store_filings(items)
    logger.info(f"Filings: stored {total}")
    return total


def get_recent_filings(ticker: str, limit: int = 5) -> list[dict]:
    return fetchall(
        """
        SELECT form_type, filing_date, title, url
        FROM filings
        WHERE ticker = :t
        ORDER BY filing_date DESC
        LIMIT :n
        """,
        {"t": ticker, "n": limit},
    )