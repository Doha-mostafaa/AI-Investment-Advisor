import re
from loguru import logger

# Banned phrases that imply guarantees
BANNED_PHRASES = [
    "guaranteed", "will definitely", "safe bet", "can't lose", "sure thing",
    "risk-free", "moon", "to the moon", "100% certain", "no risk",
    "free money", "cannot fail", "always goes up", "never loses",
    "get rich quick", "double your money",
]

# Suitability rules
SUITABILITY_RULES = {
    ("beginner", "low", "small"): {
        "blocked_topics": ["options", "leverage", "margin", "short selling", "derivatives", "futures"],
        "max_risk_recommendation": "low",
        "required_warnings": ["Consider consulting a financial advisor before investing."],
    },
    ("beginner", "low", "medium"): {
        "blocked_topics": ["leverage", "margin", "short selling", "futures"],
        "max_risk_recommendation": "medium",
        "required_warnings": ["Past performance does not guarantee future results."],
    },
}

DISCLAIMER = (
    "\n\n---\n⚠️ **Disclaimer**: This is AI-generated research for educational purposes only. "
    "It is NOT financial advice. Always consult a qualified financial advisor before making "
    "investment decisions. Past performance does not guarantee future results. "
    "Investing involves risk, including the potential loss of principal."
)


def check_banned_phrases(text: str) -> list[str]:
    """Return list of banned phrases found in text."""
    found = []
    lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            found.append(phrase)
    return found


def check_suitability(text: str, user: dict) -> dict:
    """Check if the response is suitable for the user's profile."""
    experience = user.get("experience", "intermediate")
    risk = user.get("risk_tolerance", "medium")
    budget = user.get("budget", "medium")
    
    key = (experience, risk, budget)
    rules = SUITABILITY_RULES.get(key, {})
    
    blocked = []
    if rules:
        for topic in rules.get("blocked_topics", []):
            if topic.lower() in text.lower():
                blocked.append(topic)
    
    return {
        "suitable": len(blocked) == 0,
        "blocked_topics_found": blocked,
        "required_warnings": rules.get("required_warnings", []),
    }


def apply_compliance(text: str, user: dict) -> dict:
    """Full compliance check. Returns filtered text + flags."""
    banned = check_banned_phrases(text)
    suitability = check_suitability(text, user)
    
    filtered = text
    
    # Remove banned phrases
    for phrase in banned:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        filtered = pattern.sub("[REDACTED - compliance]", filtered)
    
    # Add suitability warnings
    if suitability["required_warnings"]:
        for warning in suitability["required_warnings"]:
            if warning not in filtered:
                filtered += f"\n\n> ⚠️ {warning}"
    
    # Always add disclaimer
    if "Disclaimer" not in filtered:
        filtered += DISCLAIMER
    
    return {
        "filtered_text": filtered,
        "banned_phrases_found": banned,
        "suitability": suitability,
        "compliance_passed": len(banned) == 0 and suitability["suitable"],
        "disclaimer_added": True,
    }
