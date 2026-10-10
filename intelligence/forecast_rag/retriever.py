import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
from ingestion.db import fetchall

def retrieve_forecasts(ticker: str, top_k: int = 10) -> list[dict]:
    try:
        query = """
            SELECT 
                id, ticker, metric, horizon, target_value, target_range_low, 
                target_range_high, confidence, method, source, source_url, 
                made_at, valid_until, text_summary, accuracy_score,
                EXTRACT(EPOCH FROM (NOW() - made_at))/86400.0 AS days_since_made
            FROM forecasts
            WHERE ticker = :ticker
              AND valid_until > NOW()
              AND confidence > 0.3
              AND made_at > NOW() - INTERVAL '90 days'
              AND realized_value IS NULL
        """
        rows = fetchall(query, {"ticker": ticker})
        
        results = []
        for r in rows:
            days_since_made = r.get("days_since_made", 0)
            if days_since_made < 0:
                days_since_made = 0
                
            conf = float(r.get("confidence", 0.0))
            score = conf * (1.0 / (1 + days_since_made))
            
            acc = r.get("accuracy_score")
            if acc is not None:
                score *= float(acc)
                
            forecast = {
                "source_id": f"forecast:{r['id']}",
                "ticker": r["ticker"],
                "metric": r["metric"],
                "horizon": r["horizon"],
                "target_value": float(r["target_value"]) if r["target_value"] is not None else None,
                "target_range_low": float(r["target_range_low"]) if r["target_range_low"] is not None else None,
                "target_range_high": float(r["target_range_high"]) if r["target_range_high"] is not None else None,
                "confidence": conf,
                "method": r["method"],
                "source": r["source"],
                "source_url": r["source_url"],
                "made_at": r["made_at"].isoformat() if r["made_at"] else None,
                "valid_until": r["valid_until"].isoformat() if r["valid_until"] else None,
                "text_summary": r["text_summary"],
                "accuracy_score": float(acc) if acc is not None else None,
                "score": score
            }
            results.append(forecast)
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
        
    except Exception as e:
        print(f"Error retrieving forecasts: {e}")
        return []
