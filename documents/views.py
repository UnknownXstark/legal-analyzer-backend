# from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from users.models import ClientAssignment
from .models import Document, DocumentComment, DocumentVersion
from .serializers import DocumentSerializer, CommentSerializer, CreateCommentSerializer, DocumentVersionListSerializer, DocumentVersionDetailSerializer
from .utils import extract_text_from_pdf, extract_text_from_word, extract_text_from_txt
from .analysis import analyze_document_text
from .summarizer import generate_summary
from .permissions import IsAdmin, IsLawyer, IsDocumentParticipant
from notifications.utils import create_notification, log_activity
from django.utils import timezone
from django.db.models import Count, Q, Max
from django.contrib.auth import get_user_model
from notifications.models import ActivityLog
from ml_models.nlp_pipeline import process_document
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from payments.models import Subscription as PaymentSubscription
import os

# Create your views here.

class DocumentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user

        # 🧑‍⚖️ LAWYER — show only accepted client documents
        if user.role == "lawyer":
            client_ids = ClientAssignment.objects.filter(
                lawyer=user,
                status="accepted"
            ).values_list("client_id", flat=True)

            return Document.objects.filter(
                user_id__in=client_ids
            ).order_by("-uploaded_at")

        # 👤 INDIVIDUAL — show only own documents
        return Document.objects.filter(
            user=user
        ).order_by("-uploaded_at")

class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated] #Protected route, only for logged-in users.

    def post(self, request):
        file = request.FILES.get('file')
        title = request.data.get('title')

        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine file type
        file_type = ''
        if file.name.endswith('.pdf'):
            file_type = 'pdf'
        elif file.name.endswith('.docx'):
            file_type = 'word'
        elif file.name.endswith('.txt'):
            file_type = 'text'
        else:
            return Response({"error": "Unsupported file type"}, status=status.HTTP_400_BAD_REQUEST)
        
        document = Document.objects.create(
            user=request.user,
            title=title or file.name,
            file=file,
            file_type=file_type,
            status='pending'
        )

        create_notification(request.user, f"Document '{document.title}' uploaded successfully.")
        log_activity(request.user, "Uploaded document", {"document_id": document.id, "title": document.title})

        # Extract text after saving (step 4 in phase 4)
        file_path = document.file.path
        extracted_text = ""

        if file_type == 'pdf':
            extracted_text = extract_text_from_pdf(file_path)
        elif file_type == 'word':
            extracted_text = extract_text_from_word(file_path)
        elif file_type == 'text':
            extracted_text = extract_text_from_txt(file_path)

        document.extracted_text = extracted_text or ""
        document.save()

        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
# Summary for phase 3:
    # Checks if the user is authenticated.
    # Checks if file exists and has a supported format.
    # Saves it to the database + media folder.
    # Returns document data as JSON.
    # Route is protected so only authenticated users can upload documents.
# From here we move on to setting up routes in urls.py.

# (step 5 in phase 4) 
class DocumentDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

# Summary for phase 4:
    # After uploading, Django save the file to disk.
    # Then we open it and extract the text using the correct function.
    # The extracted text is stored inside "document.extracted_text".
    # The response still returns the same document JSON.
    # DocumentDerailView added to retrieve individual documents.
# Next we go to urls.py to set up the routes.

class DocumentAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # ----------------------------
        # 1. Find document
        # ----------------------------
        try:
            document = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not document.extracted_text:
            return Response({"error": "No extracted text available for analysis"}, status=status.HTTP_400_BAD_REQUEST)

        # ----------------------------
        # 2. SUBSCRIPTION ENFORCEMENT
        # ----------------------------
        try:
            sub = request.user.subscription
        except Exception:
            sub = None

        if sub:
            # Reset monthly if needed
            sub.reset_if_new_cycle()

            # FREE PLAN → max 3 analyses per month
            if sub.plan == "free":
                if sub.analysis_count >= 3:
                    return Response(
                        {
                            "error": "Upgrade required",
                            "remaining": 0
                        },
                        status=402  # Payment Required
                    )

        # ----------------------------
        # 3. Perform actual analysis
        # ----------------------------
        try:
            results = process_document(document.extracted_text, generate_summary_flag=True)
        except Exception:
            results = {
                "clauses_found": {},
                "entities": [],
                "summary": "",
                "risk_score": "Unknown"
            }

        document.clauses_found = results.get('clauses_found', document.clauses_found or {})
        document.risk_score = results.get('risk_score', document.risk_score)
        document.analyzed_at = timezone.now()
        document.status = 'analyzed'

        if not document.summary:
            try:
                document.summary = results.get('summary') or document.summary or ""
            except Exception:
                document.summary = document.summary or ""

        # ----------------------------
        # 4. Create new version snapshot
        # ----------------------------
        last_version = DocumentVersion.objects.filter(document=document).order_by("-version_number").first()
        next_version = (last_version.version_number + 1) if last_version else 1

        DocumentVersion.objects.create(
            document=document,
            version_number=next_version,
            content=document.extracted_text or ""
        )

        document.save()

        # ----------------------------
        # 5. INCREMENT USAGE (only for free plan)
        # ----------------------------
        if sub and sub.plan == "free":
            sub.analysis_count += 1
            sub.save()

        # ----------------------------
        # 6. Notifications/Logging + return
        # ----------------------------
        create_notification(request.user, f"Document '{document.title}' analyzed. Risk score: {document.risk_score}")
        log_activity(request.user, "Analyzed document", {"document_id": document.id, "risk": document.risk_score})

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


    
# Summary for phase 5:
    # Only logged-in users can analyze their own documents.
    # The endpoint takes a document ID (pk), finds its text, analyzes it, and updates the DB.
    # It returns the full document data, now including AI results.
# Next we go to urls.py to add the analysis route.


class DocumentReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not document.extracted_text:
            return Response({"error": "No summary available for this document"}, status=status.HTTP_400_BAD_REQUEST)
        
        summary = generate_summary(document.extracted_text)
        document.summary = summary
        document.save()

        create_notification(request.user, f"Report generated for '{document.title}'")
        log_activity(request.user, "Generated report", {"document_id": document.id})

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
# Summary for phase 6:
    # User triggers '/api/documents/<id>/report/.'
    # It checks for extracted text.
    # Runs the summarization model.
    # Saves the summary to the document and returns updated data.
# Next we add this route to urls.py.


from django.http import HttpResponse

class DocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        # --- Build the text report ---
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

        # Log & notify
        create_notification(request.user, f"Downloaded report for '{document.title}'")
        log_activity(request.user, "Downloaded report", {"document_id": document.id})

        # Return as text file
        response = HttpResponse(report_text, content_type='text/plain')
        filename = document.title.replace(" ", "_") + "_report.txt"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response





class DocumentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            document = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete file from storage
        if document.file and document.file.path:
            if os.path.exists(document.file.path):
                os.remove(document.file.path)

        document.delete()

        create_notification(request.user, f"Document '{document.title}' deleted successfully.")
        log_activity(request.user, "Deleted document", {"document_id": pk})

        return Response(
            {"message": "Document deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


class IndividualDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)
    

class LawyerDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsLawyer]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user

        client_ids = ClientAssignment.objects.filter(
            lawyer=user,
            status="accepted"
        ).values_list("client_id", flat=True)

        return Document.objects.filter(
            user_id__in=client_ids
        ).order_by("-uploaded_at")
    

class AdminDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin':
            return Document.objects.none()
        return Document.objects.all()
    
# Summary for phase 7:
    # IndividualDashboardView: filters by 'user=request.user'
    # lawyerDashboardView: for now, returns all
    # AdminDashboardView: unrestricted view (shows all uploads)
# Next we add this route to urls.py.


class LawyerDashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsLawyer]

    def get(self, request):
        lawyer = request.user

        # Get accepted clients
        client_ids = ClientAssignment.objects.filter(
            lawyer=lawyer,
            status="accepted"
        ).values_list("client_id", flat=True)

        # Only documents belonging to accepted clients
        documents = Document.objects.filter(
            user_id__in=client_ids
        )

        # ------STATS------
        total_clients = len(client_ids)

        documents_reviewed = documents.filter(status='analyzed').count()
        pending_reviews = documents.filter(status='pending').count()
        high_risk_cases = documents.filter(risk_score='High').count()

        # ------RISK DISTRIBUTION------
        risk_low = documents.filter(risk_score='Low').count()
        risk_medium = documents.filter(risk_score='Medium').count()
        risk_high = documents.filter(risk_score='High').count()

        # ------CLIENT OVERVIEW------
        clients_overview = []
        clients = (
            Document.objects.filter(user_id__in=client_ids)
            .values('user__id', 'user__username')
            .annotate(
                docs=Count("id"),
                low=Count("id", filter=Q(risk_score="Low")),
                medium=Count("id", filter=Q(risk_score="Medium")),
                high=Count("id", filter=Q(risk_score="High")),
                last_active=Max("uploaded_at")
            )
        )

        for c in clients:
            # Compute avg risk category
            total = c["low"] + c["medium"] + c["high"]
            if total == 0:
                avg = "Unknown"
            else:
                # weighted risk: High > Medium > Low
                score = (c["low"] * 1) + (c["medium"] * 2) + (c["high"] * 3)
                avg_value = score / total

                if avg_value <= 1.5:
                    avg = "Low"
                elif avg_value <= 2.3:
                    avg = "Medium"
                else:
                    avg = "High"

            clients_overview.append({
                "id": c["user__id"],
                "name": c["user__username"],
                "docs": c["docs"],
                "avgRisk": avg,
                "lastActive": c["last_active"].strftime("%Y-%m-%d") if c["last_active"] else ""
            })

        response = {
            "stats": {
                "totalClients": total_clients,
                "documentsReviewed": documents_reviewed,
                "pendingReviews": pending_reviews,
                "highRiskCases": high_risk_cases,
            },
            "riskDistribution": {
                "low": risk_low,
                "medium": risk_medium,
                "high": risk_high,
            },
            "clients": clients_overview,
        }

        return Response(response, status=200)
    

User = get_user_model()

class AdminDashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        # ------STATS------
        total_users = get_user_model().objects.count()
        documents_analyzed = Document.objects.filter(status="analyzed").count()
        active_lawyers = get_user_model().objects.filter(role="lawyer").count()

        # Example uptime (could be improved later)
        system_uptime = "99.9%"

        # ------ACTIVITY LOG------
        activity_logs = ActivityLog.objects.select_related("user").order_by("-timestamp")[:10]

        activity_logs_data = [
            {
                "id": a.id,
                "action": a.action,
                "user": a.user.username if a.user else "Unknown",
                "type": "system",  # Default classification
                "time": a.timestamp.strftime("%Y-%m-%d %H:%M"),
            }
            for a in activity_logs
        ]

        # ------RECENT USERS------
        recent_users = (
            get_user_model().objects.order_by("-date_joined")[:10]
        )

        recent_users_data = [
            {
                "id": u.id,
                "name": u.username,
                "email": u.email,
                "role": u.role,
                "joined": u.date_joined.strftime("%Y-%m-%d"),
            }
            for u in recent_users
        ]

        response = {
            "stats": {
                "totalUsers": total_users,
                "documentsAnalyzed": documents_analyzed,
                "activeLawyers": active_lawyers,
                "systemUptime": system_uptime,
            },
            "activityLog": activity_logs_data,
            "recentUsers": recent_users_data,
        }

        return Response(response, status=200)

# COMMENTS

class DocumentCommentsView(generics.ListCreateAPIView):
    """
    GET: list comments for a document (participants only)
    POST: create a new comment (participants only)
    URL: /api/documents/<pk>/comments/
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_document(self):
        doc = get_object_or_404(Document, pk=self.kwargs.get("pk"))
        # Check permission manually (object permission)
        perm = IsDocumentParticipant()
        if not perm.has_object_permission(self.request, self, doc):
            raise PermissionDenied("You do not have access to this document")
        return doc

    def get_queryset(self):
        doc = self.get_document()
        return DocumentComment.objects.filter(document=doc).order_by("created_at")

    def post(self, request, *args, **kwargs):
        doc = self.get_document()
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = DocumentComment.objects.create(
            document=doc,
            user=request.user,
            text=serializer.validated_data["text"]
        )
        # Optionally: create_notification, log_activity
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class DocumentCommentDeleteView(generics.DestroyAPIView):
    """
    DELETE: delete a comment by id
    Only comment owner or admin can delete
    URL: /api/documents/comments/<int:comment_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, comment_id, *args, **kwargs):
        comment = get_object_or_404(DocumentComment, id=comment_id)

        # Only the author or admin can delete
        if comment.user != request.user and not (request.user.role == "admin" or request.user.is_superuser):
            raise PermissionDenied("Not allowed to delete this comment")

        comment.delete()
        return Response({"message": "Comment deleted"}, status=status.HTTP_204_NO_CONTENT)


# VERSIONS

class DocumentVersionListView(generics.ListAPIView):
    """
    GET /api/documents/<pk>/versions/  -> list versions metadata
    Participants only.
    """
    serializer_class = DocumentVersionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        doc = get_object_or_404(Document, pk=self.kwargs.get("pk"))
        perm = IsDocumentParticipant()
        if not perm.has_object_permission(self.request, self, doc):
            raise PermissionDenied("You do not have access to this document")
        return DocumentVersion.objects.filter(document=doc).order_by("-version_number")


class DocumentVersionDetailView(generics.RetrieveAPIView):
    """
    GET /api/documents/versions/<int:version_id>/
    Returns the version content (participants only)
    """
    serializer_class = DocumentVersionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        version = get_object_or_404(DocumentVersion, id=self.kwargs.get("version_id"))
        doc = version.document
        perm = IsDocumentParticipant()
        if not perm.has_object_permission(self.request, self, doc):
            raise PermissionDenied("You do not have access to this version")
        return version