import re
from loguru import logger

def extract_claims_and_citations(text: str) -> list[dict]:
    """Extract sentences and check if they have [source_id] citations."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    results = []
    for sent in sentences:
        citations = re.findall(r'\[([a-z_]+:\d+)\]', sent)
        # Skip short sentences, questions, disclaimers
        is_factual = (
            len(sent) > 30
            and not sent.strip().startswith('⚠️')
            and not sent.strip().startswith('>')
            and '?' not in sent
            and 'disclaimer' not in sent.lower()
            and 'not financial advice' not in sent.lower()
        )
        results.append({
            "sentence": sent.strip(),
            "citations": citations,
            "is_factual": is_factual,
            "has_citation": len(citations) > 0,
            "needs_citation": is_factual and len(citations) == 0,
        })
    return results


def check_citations(text: str, context_sources: list[dict] = None) -> dict:
    """Check citation coverage."""
    claims = extract_claims_and_citations(text)
    factual_claims = [c for c in claims if c["is_factual"]]
    cited = [c for c in factual_claims if c["has_citation"]]
    uncited = [c for c in factual_claims if c["needs_citation"]]
    
    # Verify cited source_ids exist in context
    valid_source_ids = set()
    if context_sources:
        for s in context_sources:
            sid = s.get("source_id") or f"{s.get('source_table', 'unknown')}:{s.get('source_id', 0)}"
            valid_source_ids.add(sid)
    
    invalid_citations = []
    if valid_source_ids:
        for claim in cited:
            for cid in claim["citations"]:
                if cid not in valid_source_ids:
                    invalid_citations.append({"citation": cid, "sentence": claim["sentence"]})
    
    total_factual = len(factual_claims)
    coverage = len(cited) / total_factual if total_factual > 0 else 1.0
    
    return {
        "total_sentences": len(claims),
        "factual_claims": total_factual,
        "cited_claims": len(cited),
        "uncited_claims": len(uncited),
        "citation_coverage": round(coverage, 2),
        "invalid_citations": invalid_citations,
        "uncited_sentences": [c["sentence"] for c in uncited[:5]],  # top 5 for review
        "passed": coverage >= 0.5,  # at least 50% of factual claims cited
    }
