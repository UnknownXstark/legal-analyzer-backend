# from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from .models import Document
from .serializers import DocumentSerializer
from .utils import extract_text_from_pdf, extract_text_from_word, extract_text_from_txt
from .analysis import analyze_document_text
from .summarizer import generate_summary
from .permissions import IsAdmin, IsLawyer
from notifications.utils import create_notification, log_activity
from django.utils import timezone
import os

# Create your views here.

class DocumentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).order_by('-uploaded_at')

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
        try:
            document = Document.objects.get(pk=pk, user=request.user)
        except Document.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not document.extracted_text:
            return Response({"error": "No extracted text available for analysis"}, status=status.HTTP_400_BAD_REQUEST)
        
        results = analyze_document_text(document.extracted_text)

        # results is expected to be { clauses_found: {...}, risk_score: "Low|Medium|High" }
        document.clauses_found = results.get('clauses_found', document.clauses_found or {})
        document.risk_score = results.get('risk_score', document.risk_score)
        document.analyzed_at = timezone.now()
        document.status = 'analyzed'

        # Optionally generate a brief summary here (or keep report separate)
        # Only generate summary if it's not already present
        if not document.summary:
            try:
                document.summary = generate_summary(document.extracted_text)
            except Exception:
                # summarizer might be slow or fail — don't block analysis
                document.summary = document.summary or ""

        document.save()

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
        if user.role != 'lawyer':
            return Document.objects.none()
        # For now, show all documents; later link to assigned clients
        return Document.objects.all()
    

class AdminDashboardView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin':
            return Document.object.none()
        return Document.objects.all()
    
# Summary for phase 7:
    # IndividualDashboardView: filters by 'user=request.user'
    # lawyerDashboardView: for now, returns all
    # AdminDashboardView: unrestricted view (shows all uploads)
# Next we add this route to urls.py.