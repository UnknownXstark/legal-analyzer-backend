# from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from .models import Document
from .serializers import DocumentSerializer
from .utils import extract_text_from_pdf, extract_text_from_word, extract_text_from_txt
from .analysis import analyze_document_text
# from .summarizer import generate_summary
import os

# Create your views here.

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
            file_type=file_type
        )

        # Extract text after saving (step 4 in phase 4)
        file_path = document.file.path
        extracted_text = ""

        if file_type == 'pdf':
            extracted_text = extract_text_from_pdf(file_path)
        elif file_type == 'word':
            extracted_text = extract_text_from_word(file_path)
        elif file_type == 'text':
            extracted_text = extract_text_from_txt(file_path)

        document.extracted_text = extracted_text
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
        document.clauses_found = results['clauses_found']
        document.risk_score = results['risk_score']
        document.save()

        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
# Summary for phase 5:
    # Only logged-in users can analyze their own documents.
    # The endpoint takes a document ID (pk), finds its text, analyzes it, and updates the DB.
    # It returns the full document data, now including AI results.
# Next we go to urls.py to add the analysis route.