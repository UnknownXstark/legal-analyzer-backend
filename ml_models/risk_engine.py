# ml_models/risk_engine.py

def score_risk_from_clauses(clauses: dict) -> str:
    """
    Simple scoring:
      - Count missing required clauses. More missing => higher risk.
    """
    # Define which clauses are critical
    critical = ["confidentiality", "payment_terms", "termination", "liability"]
    missing = 0
    for k in critical:
        if not clauses.get(k, False):
            missing += 1

    if missing >= 3:
        return "High"
    if missing == 2:
        return "Medium"
    return "Low"
