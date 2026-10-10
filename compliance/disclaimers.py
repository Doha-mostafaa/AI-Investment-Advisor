STANDARD_DISCLAIMER = (
    "⚠️ **Disclaimer**: This is AI-generated research for educational purposes only. "
    "It is NOT financial advice. Always consult a qualified financial advisor before making "
    "investment decisions. Past performance does not guarantee future results. "
    "Investing involves risk, including the potential loss of principal."
)

BEGINNER_DISCLAIMER = (
    "🎓 **Important for New Investors**: This analysis is for learning purposes. "
    "Before investing any money:\n"
    "- Talk to a financial advisor\n"
    "- Never invest more than you can afford to lose\n"
    "- Diversify your investments\n"
    "- Start small and learn as you go"
)

RISK_WARNING = (
    "⚠️ **Risk Warning**: All investments carry risk. The value of investments can go "
    "down as well as up, and you may get back less than you invest."
)

def get_disclaimer(user: dict) -> str:
    experience = user.get("experience", "intermediate")
    if experience == "beginner":
        return f"\n\n---\n{BEGINNER_DISCLAIMER}\n\n{STANDARD_DISCLAIMER}"
    return f"\n\n---\n{STANDARD_DISCLAIMER}"
