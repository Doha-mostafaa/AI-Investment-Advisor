import json
import os
from datetime import datetime, timezone
from loguru import logger

AUDIT_DIR = os.path.join(os.path.dirname(__file__), '..', 'audit_data')
os.makedirs(AUDIT_DIR, exist_ok=True)

def log_query(query_id: str, query: str, ticker: str, user: dict, response: str, metadata: dict = None) -> str:
    """Log a query-response pair. Returns the log file path."""
    entry = {
        "query_id": query_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "ticker": ticker,
        "user_profile": user,
        "response_length": len(response),
        "response_preview": response[:500],
        "metadata": metadata or {},
    }
    
    filepath = os.path.join(AUDIT_DIR, f"{query_id}.json")
    with open(filepath, 'w') as f:
        json.dump(entry, f, indent=2, default=str)
    
    # Also append to the immutable log
    log_line = json.dumps(entry, default=str)
    with open(os.path.join(AUDIT_DIR, 'audit.jsonl'), 'a') as f:
        f.write(log_line + '\n')
    
    logger.info(f"Audit logged: {query_id}")
    return filepath


def get_past_answer(query_id: str) -> dict | None:
    """Retrieve a past answer by query_id."""
    filepath = os.path.join(AUDIT_DIR, f"{query_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        return json.load(f)


def list_recent(limit: int = 20) -> list[dict]:
    """List recent audit entries."""
    log_file = os.path.join(AUDIT_DIR, 'audit.jsonl')
    if not os.path.exists(log_file):
        return []
    entries = []
    with open(log_file) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:]
