from django.db import models
from django.conf import settings

# Create your models here.
class Document(models.Model):
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('word', 'Word'),
        ('text', 'Text'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # Summary for phase 3:
        # user: Connects the document to the user who uploaded it.
        # FileField: Handles file uploads automatically (we’ll connect to AWS S3 later).
        # file_type: Helps us know what kind of document it is.
        # uploaded_at: Automatically records when the document was added.
    # Then we can create a serializer for this model in serializers.py and set up views and URLs to handle document uploads and retrievals.


     # New field to store extracted text (Start of phase 4)
    extracted_text = models.TextField(blank=True, null=True)
    # Summary for phase 4:
    # "extracted_text" was addded to save the converted text.
    # Later we will run AI/NLP analysis on this field.
    # Go to utils.py

    # New fields for AI Analysis (Start of phase 5)
    clauses_found = models.JSONField(blank=True, null=True)
    risk_score = models.CharField(max_length=20, blank=True, null=True)

    # Summary for phase 5:
        # "clauses_found": stores a dictionary of clause names and their occurrences (e.g., { "Confidentiality": true, "Termination": false })
        # "risk_score": stores the final AI risk level (Low / Medium / High)
        # These fields will be populated after AI analysis.

    
    # New field for summarized report text (Phase 6)
    summary = models.TextField(blank=True, null=True)

    # Summary for phase 6:
        # We added "summary", this will hold the AI-generated summary of the document.
    # Next we create a new file called "summarizer.py" to implement the summarization logic.

    

    def __str__(self):
        return f"{self.title} - {self.user.username}"