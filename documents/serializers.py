from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
       model = Document
       fields = ['id', 'user', 'title', 'file', 'file_type', 'uploaded_at', 'extracted_text', 'summary']
       read_only_fields = ['id', 'uploaded_at', 'extracted_text', 'file_type', 'summary']
# Summary for phase 3:
    # Serializers convert Document model instances to JSON and vice versa for API interactions.
    # From here we move to the views to handle upload and retrieval logic.