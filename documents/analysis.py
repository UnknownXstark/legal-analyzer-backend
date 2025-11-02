import spacy
import re

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

# Define key legal clauses and keywords
LEGAL_CLAUSES = {
    "Confidentiality": ["confidential", "non-disclosure", "privacy"],
    "Termination": ["terminate", "termination", "expiry"],
    "Indemnity": ["indemnify", "liability", "hold harmless"],
    "Governing Law": ["governing law", "jurisdiction", "legal venue"],
    "Force Majeure": ["force majeure", "act of God", "unforeseeable circumstances"],
    "Payment": ["payment", "fee", "amount", "invoice"],
    "Obligation": ["must", "shall", "required"],
}

def analyze_document_text(text):
    doc = nlp(text.lower())

    clauses_found = {}
    risk_score = "Low"

    # Simple keyword-based clause detection
    for clause, keywords in LEGAL_CLAUSES.items():
        found = any(keyword in text.lower() for keyword in keywords)
        clauses_found[clause] = found

    # Basic risk estimation (can be made more complex later)
    high_risk_terms = ["terminate", "indemnify", "liable", "breach"]
    medium_risk_terms = ["dispute", "delay", "default"]

    if any(word in text.lower() for word in high_risk_terms):
        risk_score = "High"
    elif any(word in text.lower() for word in medium_risk_terms):
        risk_score = "Medium"

    return {
        "clauses_found": clauses_found,
        "risk_score": risk_score
    }

#Summary of the analysis function:
    # We scan the extracted text for specidic keywords.
    # Found keywords are marked as "True".
    # A quick rule-based system gives each document a risk level.
    # Later, we can swap this for a pre-trained Hugging Face model.
# Next we go to views.py to create an AI Analysis API Endpoint.