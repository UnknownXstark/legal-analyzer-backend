# ml_models/summarizer.py
import os
import requests
import time

HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")  # required

HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}

# Small helper to call HF Inference API
def generate_summary(text: str, max_retries: int = 3) -> str:
    if not HF_API_TOKEN:
        # Fail gracefully — return short fallback summary
        return (text[:800] + "...") if len(text) > 800 else text

    payload = {
        "inputs": text,
        "parameters": {"max_length": 200, "min_length": 50, "do_sample": False},
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # HF returns a list of dicts for summarization models
                if isinstance(data, list) and "summary_text" in data[0]:
                    return data[0]["summary_text"]
                # Some models return text directly
                if isinstance(data, dict) and "summary_text" in data:
                    return data["summary_text"]
                # If response is plain text
                if isinstance(data, str):
                    return data
                # Fallback to str(resp.json())
                return str(data)
            elif resp.status_code in (503, 502) and attempt < max_retries:
                time.sleep(2 * attempt)
                continue
            else:
                # Unexpected status -> return fallback
                break
        except requests.RequestException:
            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue
            break

    # Fallback summarization: truncate intelligently
    text = text.strip()
    if len(text) <= 1000:
        return text
    return text[:1000] + "..."
