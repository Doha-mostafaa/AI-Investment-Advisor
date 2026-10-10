import sys
import os
import asyncio
import uuid

# Fix path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.schemas import ChatRequest, ChatResponse, DossierResponse, HealthResponse

app = FastAPI(
    title="Multi-Agent Stock Research API",
    description="Bull/Bear/Judge debate system for stock analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health():
    from ingestion.db import healthcheck as pg_health
    from ingestion.redis_client import healthcheck as redis_health
    pg = pg_health()
    rd = redis_health()
    return HealthResponse(
        status="ok" if pg and rd else "degraded",
        postgres=pg,
        redis=rd,
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    from orchestration.graph import run_graph
    
    user = {
        "name": req.user_name,
        "experience": req.experience,
        "risk_tolerance": req.risk_tolerance,
        "budget": req.budget,
    }
    
    try:
        state = await run_graph(req.query, req.ticker, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Apply compliance
    from compliance.rules import apply_compliance
    formatted = state.get("formatted_response", "No response generated.")
    compliance = apply_compliance(formatted, user)
    
    # Audit log
    from compliance.audit_log import log_query
    query_id = str(uuid.uuid4())
    log_query(
        query_id=query_id,
        query=req.query,
        ticker=req.ticker,
        user=user,
        response=compliance["filtered_text"],
        metadata={
            "latency_ms": state.get("latency_ms"),
            "compliance_passed": compliance["compliance_passed"],
            "banned_phrases": compliance["banned_phrases_found"],
        }
    )
    
    return ChatResponse(
        query=req.query,
        ticker=req.ticker,
        formatted_response=compliance["filtered_text"],
        judge_verdict=state.get("judge_verdict"),
        bull_case=state.get("bull_output"),
        bear_case=state.get("bear_output"),
        experts={
            "fundamentals": state.get("expert_fundamentals"),
            "valuation": state.get("expert_valuation"),
            "risk": state.get("expert_risk"),
        },
        devils_advocate=state.get("devils_advocate"),
        latency_ms=state.get("latency_ms"),
        errors=state.get("errors"),
    )

@app.get("/dossier/{ticker}", response_model=DossierResponse)
async def get_dossier(ticker: str):
    from ingestion.dossier_builder import get_dossier
    ticker = ticker.upper()
    dossier = get_dossier(ticker)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Dossier not found for {ticker}")
    return DossierResponse(ticker=ticker, dossier=dossier)

@app.get("/audit")
async def list_audit():
    from compliance.audit_log import list_recent
    return list_recent(20)

@app.get("/audit/{query_id}")
async def get_audit(query_id: str):
    from compliance.audit_log import get_past_answer
    entry = get_past_answer(query_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry
