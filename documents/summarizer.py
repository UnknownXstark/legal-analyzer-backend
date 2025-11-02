from transformers import pipeline


# Load a pre-trained summarization pipline (first load might take a few seconds)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def generate_summary(text):
    if not text or len(text.split()) < 30:
        return "Not enough content to summarize."
    
    summary = summarizer(text, max_length=130, min_length=40, do_sample=False)
    return summary[0]['summary_text']

# Summary for phase 6:
    # The "facebook/bart-large-cnn" model is a widely used summarization model.
    # It condenses long text into a readable summary.
    # The function "generate_summary()" checks text length before summarizing.
# Next we integrate this into the analysis workflow in views.py.