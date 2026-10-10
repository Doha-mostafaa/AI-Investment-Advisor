import sys
import os
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ingestion import dossier_builder
from rag_index import retrieve_facts
from intelligence.forecast_rag.retriever import retrieve_forecasts
from intelligence.regime.snapshot import get_regime_snapshot

def assemble_context(query: str, user: dict, ticker: str) -> dict:
    try:
        dossier = dossier_builder.get_dossier(ticker)
    except Exception as e:
        print(f"Error getting dossier: {e}")
        dossier = None
        
    try:
        facts = retrieve_facts(ticker, query, top_k=5)
    except Exception as e:
        print(f"Error getting facts: {e}")
        facts = []
        
    try:
        forecasts = retrieve_forecasts(ticker, top_k=10)
    except Exception as e:
        print(f"Error getting forecasts: {e}")
        forecasts = []
        
    try:
        regime = get_regime_snapshot()
    except Exception as e:
        print(f"Error getting regime snapshot: {e}")
        regime = {}

    if not facts:
        facts = []

    # Format the company part based on the dossier
    if dossier:
        company = {
            "name": dossier.get("name", ticker),
            "price": dossier.get("price", {}),
            "fundamentals": dossier.get("fundamentals", {}),
            "news_7d": dossier.get("news_7d", []),
            "forecasts": dossier.get("forecasts", []),
            "risks": dossier.get("risks", []),
            "catalysts": dossier.get("catalysts", [])
        }
    else:
        company = {
            "name": ticker,
            "error": "Failed to load company dossier"
        }

    sources = []
    
    # Collect sources from facts
    for f in facts:
        if "source_id" in f and f["source_id"] not in sources:
            sources.append(f["source_id"])
            
    # Collect sources from forecasts
    for f in forecasts:
        if "source_id" in f and f["source_id"] not in sources:
            sources.append(f["source_id"])

    # Forecast notes
    retrieved_forecasts = forecasts
    if not retrieved_forecasts:
        retrieved_forecasts = []
        
    context = {
        "query": query,
        "ticker": ticker,
        "user_profile": user,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "regime": regime,
        "company": company,
        "retrieved_facts": facts,
        "retrieved_forecasts": retrieved_forecasts,
        "sources": sources
    }
    
    if not retrieved_forecasts:
        context["notes"] = "no active forecasts"
        
    return context

if __name__ == '__main__':
    user = {"name": "demo_user", "experience": "beginner", "risk_tolerance": "medium", "budget": "medium"}
    context = assemble_context("What are the upcoming catalysts for MCD?", user, "MCD")
    import json
    print(json.dumps(context, indent=2, default=str))
