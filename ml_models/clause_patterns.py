# ml_models/clause_patterns.py
import spacy
from spacy.matcher import PhraseMatcher

nlp = spacy.load("en_core_web_sm")

PATTERNS = {
    "confidentiality": ["confidentiality", "non-disclosure", "non disclosure", "confidential"],
    "termination": ["terminate", "termination", "terminate this agreement", "termination clause"],
    "payment_terms": ["payment", "payment terms", "fees", "compensation", "invoice"],
    "liability": ["liability", "indemnif", "indemnify", "limitation of liability"],
    "jurisdiction": ["governing law", "jurisdiction", "venue", "law of"],
    "warranty": ["warrant", "warranty", "representations and warranties"],
    "data_protection": ["data protection", "gdpr", "personal data", "privacy"],
}

# Build the matcher
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for key, phrases in PATTERNS.items():
    docs = [nlp.make_doc(p) for p in phrases]
    matcher.add(key, docs)


def extract_clauses(text: str) -> dict:
    """
    Returns a dictionary like {"confidentiality": True, "termination": False, ...}
    """
    doc = nlp(text[:200000])  # safety: limit extremely long text
    matches = matcher(doc)

    found = {k: False for k in PATTERNS.keys()}
    for match_id, start, end in matches:
        label = nlp.vocab.strings[match_id]
        found[label] = True

    return found
