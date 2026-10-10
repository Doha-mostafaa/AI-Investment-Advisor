import asyncio
import time
import json
import sys
import os
import re
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from orchestration.state import AgentState, new_state
from orchestration.context_assembler import assemble_context
from models.gateway import call_llm, load_prompt
from loguru import logger

async def run_agent(agent_name: str, system_prompt: str, user_message: str, model_tier: str = "strong") -> dict:
    """Run a single agent call. Returns parsed JSON or raw text."""
    try:
        raw = await asyncio.to_thread(call_llm, system_prompt, user_message, model_tier)
        
        # Try to parse JSON from the response
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
            
        # Look for JSON in ```json ... ``` blocks
        match = re.search(r'```json\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        return {"raw_text": raw}
    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}")
        return {"error": str(e)}

def build_user_message(state: AgentState) -> str:
    """Build the user message from context block for agents."""
    ctx = state.get("context_block", {})
    parts = []
    parts.append(f"QUERY: {state['query']}")
    parts.append(f"TICKER: {state['ticker']}")
    
    company = ctx.get("company", {})
    if company:
        parts.append(f"\nCOMPANY: {company.get('name', state['ticker'])}")
        parts.append(f"PRICE: {json.dumps(company.get('price', {}), default=str)}")
        parts.append(f"FUNDAMENTALS: {json.dumps(company.get('fundamentals', {}), default=str)}")
        parts.append(f"NEWS: {json.dumps(company.get('news_7d', [])[:5], default=str)}")
    
    regime = ctx.get("regime", {})
    if regime:
        parts.append(f"\nMARKET REGIME: {json.dumps(regime, default=str)}")
    
    facts = ctx.get("retrieved_facts", [])
    if facts:
        parts.append(f"\nRELEVANT FACTS:")
        for f in facts:
            parts.append(f"  [{f.get('source_id')}] {f.get('text', '')[:300]}")
    
    forecasts = ctx.get("retrieved_forecasts", [])
    if forecasts:
        parts.append(f"\nFORECASTS:")
        for f in forecasts:
            parts.append(f"  [{f.get('source_id')}] {f.get('text_summary', '')} (conf={f.get('confidence')}, accuracy={f.get('accuracy_score')})")
    
    return "\n".join(parts)

async def route(state: AgentState) -> AgentState:
    """Router: classify intent."""
    prompt = load_prompt("router")
    result = await run_agent("router", prompt, state["query"], model_tier="fast")
    state["intent"] = result.get("intent", "research")
    state["complexity"] = result.get("complexity", "complex")
    state["needs_debate"] = result.get("needs_debate", True)
    return state

async def run_bull_bear_experts(state: AgentState) -> AgentState:
    """Run Bull, Bear, and 3 Experts in PARALLEL."""
    user_msg = build_user_message(state)
    
    bull_prompt = load_prompt("bull")
    bear_prompt = load_prompt("bear")
    fund_prompt = load_prompt("experts/fundamentals")
    val_prompt = load_prompt("experts/valuation")
    risk_prompt = load_prompt("experts/risk")
    
    results = await asyncio.gather(
        run_agent("bull", bull_prompt, user_msg),
        run_agent("bear", bear_prompt, user_msg),
        run_agent("fundamentals", fund_prompt, user_msg, "fast"),
        run_agent("valuation", val_prompt, user_msg, "fast"),
        run_agent("risk", risk_prompt, user_msg, "fast"),
    )
    
    state["bull_output"] = results[0]
    state["bear_output"] = results[1]
    state["expert_fundamentals"] = results[2]
    state["expert_valuation"] = results[3]
    state["expert_risk"] = results[4]
    return state

async def debate(state: AgentState) -> AgentState:
    """One round of debate: Bull sees Bear's case, Bear sees Bull's case."""
    bull_prompt = load_prompt("bull")
    bear_prompt = load_prompt("bear")
    
    user_msg = build_user_message(state)
    
    bull_debate_msg = user_msg + f"\n\nBEAR'S ARGUMENT TO REBUT:\n{json.dumps(state.get('bear_output', {}), default=str)}"
    bear_debate_msg = user_msg + f"\n\nBULL'S ARGUMENT TO REBUT:\n{json.dumps(state.get('bull_output', {}), default=str)}"
    
    bull_reb, bear_reb = await asyncio.gather(
        run_agent("bull_rebuttal", bull_prompt + "\n\nYou are now in REBUTTAL mode. Address the bear's specific arguments.", bull_debate_msg),
        run_agent("bear_rebuttal", bear_prompt + "\n\nYou are now in REBUTTAL mode. Address the bull's specific arguments.", bear_debate_msg),
    )
    
    state["bull_rebuttal"] = bull_reb
    state["bear_rebuttal"] = bear_reb
    return state

async def judge(state: AgentState) -> AgentState:
    """Judge weighs all evidence."""
    prompt = load_prompt("judge")
    evidence = {
        "bull_case": state.get("bull_output"),
        "bear_case": state.get("bear_output"),
        "bull_rebuttal": state.get("bull_rebuttal"),
        "bear_rebuttal": state.get("bear_rebuttal"),
        "fundamentals_expert": state.get("expert_fundamentals"),
        "valuation_expert": state.get("expert_valuation"),
        "risk_expert": state.get("expert_risk"),
    }
    user_msg = build_user_message(state) + f"\n\nALL AGENT OUTPUTS:\n{json.dumps(evidence, default=str)}"
    state["judge_verdict"] = await run_agent("judge", prompt, user_msg)
    return state

async def devils_advocate(state: AgentState) -> AgentState:
    """Attack the judge's conclusion."""
    prompt = load_prompt("devils_advocate")
    user_msg = f"JUDGE'S VERDICT:\n{json.dumps(state.get('judge_verdict', {}), default=str)}"
    state["devils_advocate"] = await run_agent("devils_advocate", prompt, user_msg)
    return state

async def format_response(state: AgentState) -> AgentState:
    """Format the final response for the user."""
    is_beginner = state.get("user_profile", {}).get("experience") == "beginner"
    prompt_name = "beginner" if is_beginner else "formatter"
    prompt = load_prompt(prompt_name)
    
    all_outputs = {
        "query": state["query"],
        "ticker": state["ticker"],
        "judge_verdict": state.get("judge_verdict"),
        "bull_case": state.get("bull_output"),
        "bear_case": state.get("bear_output"),
        "experts": {
            "fundamentals": state.get("expert_fundamentals"),
            "valuation": state.get("expert_valuation"),
            "risk": state.get("expert_risk"),
        },
        "devils_advocate": state.get("devils_advocate"),
        "regime": state.get("context_block", {}).get("regime"),
        "company_price": state.get("context_block", {}).get("company", {}).get("price"),
    }
    
    result = await run_agent("formatter", prompt, json.dumps(all_outputs, default=str), "fast")
    state["formatted_response"] = result.get("raw_text", "") if "raw_text" in result else json.dumps(result, indent=2, default=str)
    return state

async def run_graph(query: str, ticker: str, user: dict = None) -> dict:
    """Main entry point. Runs the full DAG and returns results."""
    if user is None:
        user = {"name": "demo_user", "experience": "intermediate", "risk_tolerance": "medium", "budget": "medium"}
    
    start = time.time()
    
    # 1. Assemble context
    context = assemble_context(query, user, ticker)
    state = new_state(query, ticker, user, context)
    
    try:
        # 2. Route
        state = await route(state)
        
        # 3. Run Bull/Bear/Experts in parallel
        state = await run_bull_bear_experts(state)
        
        # 4. Debate round
        if state.get("needs_debate", True):
            state = await debate(state)
        
        # 5. Judge
        state = await judge(state)
        
        # 6. Devil's Advocate
        state = await devils_advocate(state)
        
        # 7. Format (skip verification for now - Person 5)
        state = await format_response(state)
        
    except Exception as e:
        logger.error(f"Graph failed: {e}")
        state["errors"] = state.get("errors", []) + [str(e)]
    
    state["end_time"] = datetime.now(timezone.utc).isoformat()
    state["latency_ms"] = (time.time() - start) * 1000
    
    return state

def run_sync(query: str, ticker: str, user: dict = None) -> dict:
    """Synchronous wrapper."""
    return asyncio.run(run_graph(query, ticker, user))

if __name__ == "__main__":
    result = run_sync("Should I buy MCD stock?", "MCD")
    print(f"\\nLatency: {result.get('latency_ms', 0):.0f}ms")
    print(f"Judge: {json.dumps(result.get('judge_verdict'), indent=2, default=str)}")
    print(f"\\nFormatted Response:\\n{result.get('formatted_response', 'N/A')}")
