from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    query: str
    ticker: str = "MCD"
    user_name: str = "demo_user"
    experience: str = "intermediate"  # beginner | intermediate | advanced
    risk_tolerance: str = "medium"     # low | medium | high
    budget: str = "medium"             # small | medium | large

class AgentOutput(BaseModel):
    agent_name: str
    output: dict
    
class ChatResponse(BaseModel):
    query: str
    ticker: str
    formatted_response: str
    judge_verdict: Optional[dict] = None
    bull_case: Optional[dict] = None
    bear_case: Optional[dict] = None
    experts: Optional[dict] = None
    devils_advocate: Optional[dict] = None
    latency_ms: Optional[float] = None
    errors: Optional[list] = None

class DossierResponse(BaseModel):
    ticker: str
    dossier: dict

class HealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool
