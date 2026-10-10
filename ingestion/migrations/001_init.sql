-- Core tables for Person 1
-- All tables have bitemporal columns: event_time (when it happened) + ingest_time (when we learned)

CREATE TABLE IF NOT EXISTS prices (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL DEFAULT 'yfinance',
    UNIQUE(ticker, ts)
);

CREATE INDEX idx_prices_ticker_ts ON prices (ticker, ts DESC);

CREATE TABLE IF NOT EXISTS news (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT,
    headline TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    source TEXT,
    url TEXT,
    author TEXT,
    sentiment NUMERIC,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw JSONB
);

CREATE INDEX idx_news_ticker_time ON news (ticker, event_time DESC);

CREATE TABLE IF NOT EXISTS filings (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    form_type TEXT NOT NULL,
    filing_date DATE NOT NULL,
    accession_no TEXT UNIQUE,
    title TEXT,
    url TEXT,
    content TEXT,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw JSONB
);

CREATE INDEX idx_filings_ticker_date ON filings (ticker, filing_date DESC);

CREATE TABLE IF NOT EXISTS forecasts (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    horizon TEXT NOT NULL,
    target_value NUMERIC,
    target_range_low NUMERIC,
    target_range_high NUMERIC,
    confidence NUMERIC,
    method TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT,
    made_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    realized_value NUMERIC,
    realized_at TIMESTAMPTZ,
    accuracy_score NUMERIC,
    text_summary TEXT,
    metadata JSONB,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_forecasts_ticker_metric ON forecasts (ticker, metric, made_at DESC);
CREATE INDEX idx_forecasts_valid ON forecasts (valid_until) WHERE realized_value IS NULL;

CREATE TABLE IF NOT EXISTS fundamentals (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    as_of DATE NOT NULL,
    pe NUMERIC,
    pe_5y_avg NUMERIC,
    peg NUMERIC,
    revenue_ttm NUMERIC,
    margin NUMERIC,
    debt_ebitda NUMERIC,
    market_cap NUMERIC,
    dividend_yield NUMERIC,
    raw JSONB,
    event_time TIMESTAMPTZ NOT NULL,
    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(ticker, as_of)
);

CREATE TABLE IF NOT EXISTS dossiers (
    ticker TEXT PRIMARY KEY,
    as_of TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);