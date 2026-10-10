"""
Map free-text company mentions to tickers.
For demo: simple alias dictionary. Production: use NER + knowledge graph.
"""
import re

ALIASES = {
    "AAPL": ["apple", "apple inc", "aapl", "iphone maker"],
    "MSFT": ["microsoft", "msft", "windows maker", "azure"],
    "GOOGL": ["google", "alphabet", "googl", "goog"],
    "AMZN": ["amazon", "amzn", "aws"],
    "MCD":  ["mcdonald", "mcdonalds", "mcdonald's", "mcd", "golden arches"],
    "NVDA": ["nvidia", "nvda"],
    "TSLA": ["tesla", "tsla", "elon musk company"],
    "JPM":  ["jpmorgan", "jp morgan", "jpm", "jamie dimon"],
    "KO":   ["coca-cola", "coca cola", "coke", "ko"],
    "XOM":  ["exxon", "exxonmobil", "xom"],
}

_LOOKUP = {alias: ticker for ticker, aliases in ALIASES.items() for alias in aliases}

def resolve(text: str) -> list[str]:
    """Return list of tickers mentioned in text."""
    if not text:
        return []
    lower = text.lower()
    found = set()
    for alias, ticker in _LOOKUP.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            found.add(ticker)
    return list(found)

def resolve_one(text: str) -> str | None:
    tickers = resolve(text)
    return tickers[0] if tickers else None