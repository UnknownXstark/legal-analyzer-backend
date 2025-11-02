from django.urls import path
from .views import DocumentUploadView, DocumentDetailView, DocumentAnalysisView, DocumentReportView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('<int:pk>/analyze/', DocumentAnalysisView.as_view(), name='document-analyze'),
    path('<int:pk>/report/', DocumentReportView.as_view(), name='document-report')
]


# Summary for phase 3:
    # Sets up the URL route for document uploads, linking to the DocumentUploadView.
    # backend/urls.py will include this file to integrate document routes into the main app.

# Summary for phase 4:
    # Adds a route to view individual document details via DocumentDetailView.

# Summary for phase 5:
    # Adds a route to 

# Summary for phase 6:
    # Added the route for report generation.