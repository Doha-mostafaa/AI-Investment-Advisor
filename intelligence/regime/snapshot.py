import urllib.request
import csv
import io
import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from ingestion.redis_client import set_json, get_json

def _fetch_fred_latest(series_id: str) -> float:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read().decode('utf-8')
    
    reader = csv.reader(io.StringIO(content))
    next(reader) # skip header
    
    last_val = None
    for row in reader:
        if len(row) >= 2 and row[1].strip() != '.':
            try:
                last_val = float(row[1])
            except ValueError:
                pass
                
    if last_val is None:
        raise ValueError(f"No valid data found for {series_id}")
    return last_val

def get_regime_snapshot() -> dict:
    cache_key = "regime_snapshot"
    try:
        cached = get_json(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    try:
        fed_funds = _fetch_fred_latest("FEDFUNDS")
        treasury_10y = _fetch_fred_latest("DGS10")
        vix = _fetch_fred_latest("VIXCLS")
        
        regime = "neutral"
        if vix < 20:
            regime = "risk-on"
        elif vix > 30:
            regime = "risk-off"
            
        rate_env = "moderate"
        if fed_funds > 4:
            rate_env = "high"
        elif fed_funds < 2:
            rate_env = "low"
            
        summary = f"Market regime: {regime}. Fed funds at {fed_funds}%, 10Y Treasury at {treasury_10y}%, VIX at {vix}."
        
        snapshot = {
            "as_of": datetime.datetime.utcnow().isoformat() + "Z",
            "fed_funds_rate": fed_funds,
            "treasury_10y": treasury_10y,
            "vix": vix,
            "regime": regime,
            "rate_environment": rate_env,
            "summary": summary
        }
        
        try:
            set_json(cache_key, snapshot, ttl_seconds=3600)
        except Exception:
            pass
            
        return snapshot
        
    except Exception as e:
        print(f"Error fetching regime snapshot: {e}")
        return {
            "as_of": datetime.datetime.utcnow().isoformat() + "Z",
            "fed_funds_rate": 5.33,
            "treasury_10y": 4.12,
            "vix": 13.5,
            "regime": "risk-on",
            "rate_environment": "high",
            "summary": "Market regime: risk-on (fallback). Network error fetching latest data."
        }
