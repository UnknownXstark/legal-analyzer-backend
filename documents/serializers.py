# from rest_framework import serializers
# from .models import Document

# class DocumentSerializer(serializers.ModelSerializer):
#     class Meta:
#        model = Document
#        fields = ['id', 'user', 'title', 'file', 'file_type', 'uploaded_at', 'extracted_text', 'summary']
#        read_only_fields = ['id', 'uploaded_at', 'extracted_text', 'file_type', 'summary']
# # Summary for phase 3:
#     # Serializers convert Document model instances to JSON and vice versa for API interactions.
#     # From here we move to the views to handle upload and retrieval logic.

from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    uploaded_at = serializers.DateTimeField(format=None)  # let frontend format if needed
    analyzed_at = serializers.DateTimeField(format=None, allow_null=True, required=False)

    class Meta:
        model = Document
        fields = [
            'id',
            'user',
            'title',
            'file',            # will return URL string (or filename)
            'file_type',
            'uploaded_at',
            'extracted_text',
            'clauses_found',
            'risk_score',
            'summary',
            'analyzed_at',
            'status',
        ]
        read_only_fields = ['id', 'uploaded_at', 'extracted_text', 'clauses_found', 'risk_score', 'summary', 'analyzed_at', 'status', 'file']

    def get_file(self, obj):
        # Return URL if available, otherwise the filename
        try:
            if obj.file and hasattr(obj.file, 'url'):
                return obj.file.url
        except Exception:
            pass
        return str(obj.file)
