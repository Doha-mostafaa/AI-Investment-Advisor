from typing import TypedDict, Optional
from datetime import datetime, timezone
import json

class AgentState(TypedDict, total=False):
    # Input
    query: str
    ticker: str
    user_profile: dict
    context_block: dict  # Contract B from context_assembler
    
    # Router
    intent: str
    complexity: str
    needs_debate: bool
    
    # Agent outputs
    bull_output: dict
    bear_output: dict
    expert_fundamentals: dict
    expert_valuation: dict
    expert_risk: dict
    
    # Debate
    bull_rebuttal: dict
    bear_rebuttal: dict
    
    # Judge
    judge_verdict: dict
    devils_advocate: dict
    
    # Verification
    verification_result: dict
    compliance_result: dict
    
    # Final
    formatted_response: str
    sources: list
    
    # Meta
    start_time: str
    end_time: str
    latency_ms: float
    errors: list

def new_state(query: str, ticker: str, user: dict, context: dict) -> AgentState:
    return {
        "query": query,
        "ticker": ticker,
        "user_profile": user,
        "context_block": context,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "errors": []
    }

def serialize_state(state: AgentState) -> dict:
    return json.loads(json.dumps(state, default=str))
