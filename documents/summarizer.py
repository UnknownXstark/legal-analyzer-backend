from transformers import pipeline


# Load a pre-trained summarization pipline (first load might take a few seconds)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def chunk_text(text, max_chunk_size=350):
    words = text.split()
    for i in range(0, len(words), max_chunk_size):
        yield " ".join(words[i:i + max_chunk_size])

def generate_summary(text):
    if not text or len(text.split()) < 30:
        return "Not enough content to summarize."
    
    text = text.strip()

    # Break text into smaller pieces if its too long
    chunks = list(chunk_text(text))
    summaries = []

    for chunk in chunks:
        try:
            result = summarizer(chunk, max_length=130, min_length=40, do_sample=False)
            summaries.append(result[0]['summary_text'])
        except Exception as e:
            summaries.append(f"[Chunk skipped due to model error: {str(e)}]")
    
    final_summary = " ".join(summaries)
    return final_summary if final_summary else "Could not generate summary."

# Summary for phase 6:
    # The "facebook/bart-large-cnn" model is a widely used summarization model.
    # It condenses long text into a readable summary.
    # The function "generate_summary()" checks text length before summarizing.

# After testing with the initail function, the uploaded document text was too large for the summarizer to process in one go.
# Models like BART and T5 can only handle a few pages of text at once.
# so to fix this, I modified the summarizer so it splits long text into smaller chuncks, 
    #  summarizes each part, then combines the summaries into one clean report.


# The new helper function chunk_text() breaks your text into smaller segments (each about 900 words).
# Each chunk is summarized individually.
# Then we combine all mini-summaries into a single readable summary.
# This prevents the index out of range issue, because the model never sees overly long text at once.

# Next we integrate this into the analysis workflow in views.py.