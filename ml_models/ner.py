# ml_models/ner.py
import spacy
nlp = spacy.load("en_core_web_sm")

def extract_entities(text: str) -> list:
    doc = nlp(text[:200000])
    entities = []
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start_char": ent.start_char,
            "end_char": ent.end_char
        })
    return entities
