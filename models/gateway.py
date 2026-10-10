import os
import httpx
import json
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model routing
MODEL_TIERS = {
    "fast": "openai/gpt-oss-20b",      # router, formatter
    "strong": "openai/gpt-oss-120b",  # bull, bear, judge, devil
}

def call_llm(system_prompt: str, user_message: str, model_tier: str = "strong", temperature: float = 0.3, max_tokens: int = 2000) -> str:
    """Call Groq API. Returns the text response."""
    try:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        model = MODEL_TIERS.get(model_tier, MODEL_TIERS["strong"])
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"} if "RESPONSE FORMAT:" in system_prompt and "{" in system_prompt else None
        }
        
        # Remove response_format if None
        if data["response_format"] is None:
            del data["response_format"]

        response = httpx.post(GROQ_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return json.dumps({"error": str(e)})

def load_prompt(name: str) -> str:
    """Reads prompt from prompts directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "orchestration", "prompts", f"{name}.txt")
    if not os.path.exists(prompt_path):
        prompt_path = os.path.join(base_dir, "orchestration", "prompts", "experts", f"{name}.txt")
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt {name}: {e}")
        return ""
