# from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from users.models import ClientAssignment, User
from users.permissions import IsLawyer, IsClient, IsAdmin
from .models import Document, DocumentComment, DocumentVersion, SharedDocument
from .serializers import (
    DocumentSerializer,
    CommentSerializer,
    CreateCommentSerializer,
    DocumentVersionListSerializer,
    DocumentVersionDetailSerializer,
    SharedDocumentSerializer,
)
from .utils import extract_text_from_pdf, extract_text_from_word, extract_text_from_txt
from .analysis import analyze_document_text
from .summarizer import generate_summary
from .permissions import IsDocumentParticipant
from notifications.utils import create_notification, log_activity
from django.utils import timezone
from django.db.models import Count, Q, Max
from django.contrib.auth import get_user_model
from notifications.models import ActivityLog
from ml_models.nlp_pipeline import process_document
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from payments.models import Subscription as PaymentSubscription
import os


# ============================================================
#   SHARED ACCESS LOGIC FOR ALL DOCUMENT ENDPOINTS
# ============================================================
def user_has_access_to_document(request, document):
    # Owner always allowed
    if document.user == request.user:
        return True

    # Admin always allowed
    if request.user.role == "admin" or request.user.is_superuser:
        return True

    # Shared with client AND accepted
    share = SharedDocument.objects.filter(
        document=document,
        client=request.user,
        status='accepted'
    ).exists()

    if share:
        return True

    return False


# ============================================================
#   DOCUMENT LIST
# ============================================================
class DocumentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user

        # Lawyer → see accepted clients' documents
        if user.role == "lawyer":
            client_ids = ClientAssignment.objects.filter(
                lawyer=user,
                status="accepted"
            ).values_list("client_id", flat=True)

            return Document.objects.filter(user_id__in=client_ids).order_by("-uploaded_at")

        # Client → only own documents
        return Document.objects.filter(user=user).order_by("-uploaded_at")


# ============================================================
#   UPLOAD DOCUMENT
# ============================================================
class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        title = request.data.get('title')

        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        # File type detection
        if file.name.endswith('.pdf'):
            file_type = 'pdf'
        elif file.name.endswith('.docx'):
            file_type = 'word'
        elif file.name.endswith('.txt'):
            file_type = 'text'
        else:
            return Response({"error": "Unsupported file type"}, status=400)

        document = Document.objects.create(
            user=request.user,
            title=title or file.name,
            file=file,
            file_type=file_type,
            status='pending'
        )

        # Extract text
        file_path = document.file.path
        if file_type == 'pdf':
            extracted_text = extract_text_from_pdf(file_path)
        elif file_type == 'word':
            extracted_text = extract_text_from_word(file_path)
        else:
            extracted_text = extract_text_from_txt(file_path)

        document.extracted_text = extracted_text or ""
        document.save()

        create_notification(request.user, f"Document '{document.title}' uploaded successfully.")
        log_activity(request.user, "Uploaded document", {"document_id": document.id})

        return Response(DocumentSerializer(document).data, status=201)


# ============================================================
#   DOCUMENT DETAIL
# ============================================================
class DocumentDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def get(self, request, *args, **kwargs):
        document = self.get_object()

        if not user_has_access_to_document(request, document):
            return Response({"error": "Not allowed"}, status=403)

        return super().get(request, *args, **kwargs)


# ============================================================
#   ANALYZE DOCUMENT
# ============================================================
class DocumentAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # Only document owner can analyze their own document
        try:
            document = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        if not document.extracted_text:
            return Response({"error": "No extracted text available"}, status=400)

        # Subscription
        try:
            sub = request.user.subscription
        except Exception:
            sub = None

        if sub:
            sub.reset_if_new_cycle()
            if sub.plan == "free" and sub.analysis_count >= 3:
                return Response({"error": "Upgrade required", "remaining": 0}, status=402)

        try:
            results = process_document(document.extracted_text, generate_summary_flag=True)
        except Exception:
            results = {
                "clauses_found": {},
                "entities": [],
                "summary": "",
                "risk_score": "Unknown"
            }

        # Save results
        document.clauses_found = results.get("clauses_found", document.clauses_found)
        document.risk_score = results.get("risk_score", document.risk_score)
        document.summary = results.get("summary", document.summary)
        document.analyzed_at = timezone.now()
        document.status = "analyzed"

        # Versioning
        last_version = DocumentVersion.objects.filter(document=document).order_by("-version_number").first()
        next_version = last_version.version_number + 1 if last_version else 1

        DocumentVersion.objects.create(
            document=document,
            version_number=next_version,
            content=document.extracted_text or ""
        )

        document.save()

        # Increment usage
        if sub and sub.plan == "free":
            sub.analysis_count += 1
            sub.save()

        return Response(DocumentSerializer(document).data, status=200)


# ============================================================
#   SUMMARIZE DOCUMENT
# ============================================================
class DocumentReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        if not user_has_access_to_document(request, document):
            return Response({"error": "Not allowed"}, status=403)

        if not document.extracted_text:
            return Response({"error": "No extracted text available"}, status=400)

        document.summary = generate_summary(document.extracted_text)
        document.save()

        return Response(DocumentSerializer(document).data, status=200)


# ============================================================
#   DOWNLOAD DOCUMENT REPORT
# ============================================================
class DocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        if not user_has_access_to_document(request, document):
            return Response({"error": "Not allowed"}, status=403)

        report_text = f"""
DOCUMENT REPORT
======================
Title: {document.title}
Generated: {document.analyzed_at}
Risk Level: {document.risk_score}

SUMMARY:
{document.summary}

CLAUSES:
{document.clauses_found}
""".strip()

        response = HttpResponse(report_text, content_type="text/plain")
        response['Content-Disposition'] = f'attachment; filename="{document.title}_report.txt"'

        return response


# ============================================================
#   DELETE DOCUMENT
# ============================================================
class DocumentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        if not user_has_access_to_document(request, document):
            return Response({"error": "Not allowed"}, status=403)

        if document.file and os.path.exists(document.file.path):
            os.remove(document.file.path)

        document.delete()

        return Response({"message": "Document deleted successfully"}, status=204)


# ============================================================
#   DASHBOARDS
# ============================================================
class IndividualDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class LawyerDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsLawyer]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        lawyer = self.request.user
        client_ids = ClientAssignment.objects.filter(
            lawyer=lawyer,
            status="accepted"
        ).values_list("client_id", flat=True)

        return Document.objects.filter(user_id__in=client_ids).order_by("-uploaded_at")


class AdminDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.all()


# ============================================================
#   LAWYER ANALYTICS
# ============================================================
class LawyerDashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsLawyer]

    def get(self, request):
        lawyer = request.user

        client_ids = ClientAssignment.objects.filter(
            lawyer=lawyer,
            status="accepted"
        ).values_list("client_id", flat=True)

        documents = Document.objects.filter(user_id__in=client_ids)

        stats = {
            "totalClients": len(client_ids),
            "documentsReviewed": documents.filter(status="analyzed").count(),
            "pendingReviews": documents.filter(status="pending").count(),
            "highRiskCases": documents.filter(risk_score="High").count(),
        }

        riskDistribution = {
            "low": documents.filter(risk_score="Low").count(),
            "medium": documents.filter(risk_score="Medium").count(),
            "high": documents.filter(risk_score="High").count(),
        }

        clients = (
            documents.values('user__id', 'user__username')
            .annotate(
                docs=Count("id"),
                low=Count("id", filter=Q(risk_score="Low")),
                medium=Count("id", filter=Q(risk_score="Medium")),
                high=Count("id", filter=Q(risk_score="High")),
                last_active=Max("uploaded_at")
            )
        )

        formatted_clients = []
        for c in clients:
            total = c["low"] + c["medium"] + c["high"]
            if total == 0:
                avg = "Unknown"
            else:
                score = (c["low"] * 1) + (c["medium"] * 2) + (c["high"] * 3)
                avg_value = score / total
                avg = "Low" if avg_value <= 1.5 else "Medium" if avg_value <= 2.3 else "High"

            formatted_clients.append({
                "id": c["user__id"],
                "name": c["user__username"],
                "docs": c["docs"],
                "avgRisk": avg,
                "lastActive": c["last_active"].strftime("%Y-%m-%d") if c["last_active"] else ""
            })

        return Response({
            "stats": stats,
            "riskDistribution": riskDistribution,
            "clients": formatted_clients
        })


# ============================================================
#   ADMIN ANALYTICS
# ============================================================
User = get_user_model()

class AdminDashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_users = User.objects.count()
        documents_analyzed = Document.objects.filter(status="analyzed").count()
        active_lawyers = User.objects.filter(role="lawyer").count()
        system_uptime = "99.9%"

        activity_logs = ActivityLog.objects.select_related("user").order_by("-timestamp")[:10]

        recent_users = User.objects.order_by("-date_joined")[:10]

        return Response({
            "stats": {
                "totalUsers": total_users,
                "documentsAnalyzed": documents_analyzed,
                "activeLawyers": active_lawyers,
                "systemUptime": system_uptime,
            },
            "activityLog": [
                {
                    "id": a.id,
                    "action": a.action,
                    "user": a.user.username if a.user else "Unknown",
                    "type": "system",
                    "time": a.timestamp.strftime("%Y-%m-%d %H:%M"),
                }
                for a in activity_logs
            ],
            "recentUsers": [
                {
                    "id": u.id,
                    "name": u.username,
                    "email": u.email,
                    "role": u.role,
                    "joined": u.date_joined.strftime("%Y-%m-%d"),
                }
                for u in recent_users
            ]
        })


# ============================================================
#   COMMENTS
# ============================================================
class DocumentCommentsView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer

    def get_document(self):
        doc = get_object_or_404(Document, pk=self.kwargs.get("pk"))
        perm = IsDocumentParticipant()
        if not perm.has_object_permission(self.request, self, doc):
            raise PermissionDenied("You do not have access to this document")
        return doc

    def get_queryset(self):
        return DocumentComment.objects.filter(document=self.get_document()).order_by("created_at")

    def post(self, request, *args, **kwargs):
        doc = self.get_document()
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = DocumentComment.objects.create(
            document=doc,
            user=request.user,
            text=serializer.validated_data["text"]
        )

        return Response(CommentSerializer(comment).data, status=201)


class DocumentCommentDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, comment_id):
        comment = get_object_or_404(DocumentComment, id=comment_id)

        if comment.user != request.user and not (request.user.role == "admin" or request.user.is_superuser):
            raise PermissionDenied("Not allowed")

        comment.delete()
        return Response({"message": "Comment deleted"}, status=204)


# ============================================================
#   VERSIONS
# ============================================================
class DocumentVersionListView(generics.ListAPIView):
    serializer_class = DocumentVersionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        doc = get_object_or_404(Document, pk=self.kwargs.get("pk"))
        perm = IsDocumentParticipant()
        if not perm.has_object_permission(self.request, self, doc):
            raise PermissionDenied("Not allowed")
        return DocumentVersion.objects.filter(document=doc).order_by("-version_number")


class DocumentVersionDetailView(generics.RetrieveAPIView):
    serializer_class = DocumentVersionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        version = get_object_or_404(DocumentVersion, id=self.kwargs.get("version_id"))
        doc = version.document
        perm = IsDocumentParticipant()
        if not perm.has_object_permission(self.request, self, doc):
            raise PermissionDenied("Not allowed")
        return version


# ============================================================
#   SHARE DOCUMENT
# ============================================================
class ShareDocumentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        document_id = request.data.get("document_id")
        client_id = request.data.get("client_id")

        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        if document.user != request.user:
            return Response({"error": "You can only share your own documents"}, status=403)

        if request.user.role != "lawyer":
            return Response({"error": "Only lawyers can share documents"}, status=403)

        try:
            client = User.objects.get(id=client_id)
        except User.DoesNotExist:
            return Response({"error": "Client not found"}, status=404)

        assignment = request.user.clients.filter(client=client).first()
        if not assignment:
            return Response({"error": "You are not assigned to this client"}, status=403)

        shared, created = SharedDocument.objects.get_or_create(
            document=document,
            lawyer=request.user,
            client=client
        )

        if not created:
            return Response({"message": "Document already shared"}, status=200)

        return Response(SharedDocumentSerializer(shared).data, status=201)


class AcceptSharedDocumentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, share_id):
        try:
            shared = SharedDocument.objects.get(id=share_id, client=request.user)
        except SharedDocument.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        shared.status = "accepted"
        shared.save()
        return Response({"message": "Document accepted"}, status=200)


class DeclineSharedDocumentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, share_id):
        try:
            shared = SharedDocument.objects.get(id=share_id, client=request.user)
        except SharedDocument.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        shared.status = "declined"
        shared.save()
        return Response({"message": "Document declined"}, status=200)


class LawyerSharedDocumentsList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "lawyer":
            return Response({"error": "Not allowed"}, status=403)

        shares = SharedDocument.objects.filter(lawyer=request.user)
        return Response(SharedDocumentSerializer(shares, many=True).data)


class ClientSharedDocumentsList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "client":
            return Response({"error": "Not allowed"}, status=403)

        shares = SharedDocument.objects.filter(client=request.user)
        return Response(SharedDocumentSerializer(shares, many=True).data)
