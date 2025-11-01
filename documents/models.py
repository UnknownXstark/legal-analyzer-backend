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


    

    def __str__(self):
        return f"{self.title} - {self.user.username}"