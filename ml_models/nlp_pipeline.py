# ml_models/nlp_pipeline.py
from .clause_patterns import extract_clauses
from .ner import extract_entities
from .ai_summarizer import generate_summary
from .risk_engine import score_risk_from_clauses

def process_document(text: str, generate_summary_flag: bool = True) -> dict:
    """
    Main entrypoint called from Django.
    Returns a dict:
      {
        "clauses_found": {...},
        "entities": [...],
        "summary": "...",
        "risk_score": "Low|Medium|High"
      }
    """
    text = text or ""
    # 1. Clause extraction
    clauses = extract_clauses(text)

    # 2. Entity extraction
    entities = extract_entities(text)

    # 3. Summarization (call HF)
    summary = None
    if generate_summary_flag:
        try:
            summary = generate_summary(text)
        except Exception:
            summary = (text[:800] + "...") if len(text) > 800 else text

    # 4. Risk scoring
    risk = score_risk_from_clauses(clauses)

    return {
        "clauses_found": clauses,
        "entities": entities,
        "summary": summary,
        "risk_score": risk
    }
