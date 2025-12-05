from django.db import models
from django.conf import settings

class Document(models.Model):
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('word', 'Word'),
        ('text', 'Text'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('analyzed', 'Analyzed'),
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

    # Extracted text
    extracted_text = models.TextField(blank=True, null=True)

    # AI analysis fields
    clauses_found = models.JSONField(blank=True, null=True)
    risk_score = models.CharField(max_length=20, blank=True, null=True)

    # When analysis was performed
    analyzed_at = models.DateTimeField(blank=True, null=True)

    # Status flag (pending/analyzed)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Summarization
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class DocumentComment(models.Model):
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="comments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_comments"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.document.title} at {self.created_at}"


class DocumentVersion(models.Model):
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="versions"
    )
    version_number = models.IntegerField()
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("document", "version_number")
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"
    

class SharedDocument(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="shares")
    lawyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shared_documents_as_lawyer")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shared_documents_as_client")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('document', 'client')  # Prevent duplicate invitations

    def __str__(self):
        return f"{self.document} shared with {self.client} ({self.status})"
