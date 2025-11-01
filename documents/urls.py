from django.urls import path
from .views import DocumentUploadView, DocumentDetailView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
]


# Summary for phase 3:
    # Sets up the URL route for document uploads, linking to the DocumentUploadView.
    # backend/urls.py will include this file to integrate document routes into the main app.

# Summary for phase 4:
    # Adds a route to view individual document details via DocumentDetailView.