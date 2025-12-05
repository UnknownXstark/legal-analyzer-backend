from rest_framework import serializers
from .models import Document, DocumentComment, DocumentVersion, SharedDocument
from django.contrib.auth import get_user_model

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
    


User = get_user_model()

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DocumentComment
        fields = ["id", "document", "user", "text", "created_at"]
        read_only_fields = ["id", "user", "created_at", "document"]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "email": obj.user.email,
            "role": obj.user.role
        }


class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentComment
        fields = ["text"]


class DocumentVersionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ["id", "version_number", "created_at"]


class DocumentVersionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ["id", "version_number", "content", "created_at"]

class SharedDocumentSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source="lawyer.username", read_only=True)
    client_name = serializers.CharField(source="client.username", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = SharedDocument
        fields = "__all__"
