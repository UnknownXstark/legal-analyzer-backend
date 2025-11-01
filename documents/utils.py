import PyPDF2
import docx

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()

def extract_text_from_word(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()
    

# Summaryp for phase 4:
    # Each function handles one file type.
    # The text is read and returned as a plain string.
    # Later, this text will feed into the AI/NLP pipeline.