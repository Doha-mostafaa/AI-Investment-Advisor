from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class Price(BaseModel):
    ticker: str
    ts: datetime
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]
    event_time: datetime
    source: str = "yfinance"

class NewsItem(BaseModel):
    ticker: Optional[str]
    headline: str
    summary: Optional[str]
    content: Optional[str]
    source: Optional[str]
    url: str
    author: Optional[str]
    sentiment: Optional[float]
    event_time: datetime

class Filing(BaseModel):
    ticker: str
    form_type: str
    filing_date: date
    accession_no: str
    title: Optional[str]
    url: str
    content: Optional[str]
    event_time: datetime

class Forecast(BaseModel):
    ticker: str
    metric: str
    horizon: str
    target_value: Optional[float]
    target_range_low: Optional[float]
    target_range_high: Optional[float]
    confidence: Optional[float]
    method: str
    source: str
    source_url: Optional[str]
    made_at: datetime
    valid_until: datetime
    text_summary: str

# Contract A — Dossier output (frozen interface)
class DossierSource(BaseModel):
    id: int
    name: str
    date: str
    url: str

class DossierNews(BaseModel):
    headline: str
    source: str
    url: str
    event_time: str
    sentiment: Optional[float] = None

class DossierForecast(BaseModel):
    metric: str
    horizon: str
    target: Optional[float]
    range: Optional[List[float]] = None
    confidence: Optional[float]
    method: str
    source: str
    made_at: str
    valid_until: str
    source_accuracy: Optional[float] = None
    n_historical: Optional[int] = None

class Dossier(BaseModel):
    ticker: str
    name: str
    as_of: str
    price: dict
    fundamentals: dict
    news_7d: List[DossierNews]
    projects: List[dict] = []
    geopolitical: List[dict] = []
    risks: List[str] = []
    catalysts: List[str] = []
    forecasts: List[DossierForecast] = []
    quant: dict = {}
    sources: List[DossierSource] = []