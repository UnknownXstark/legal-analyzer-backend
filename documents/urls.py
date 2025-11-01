from django.urls import path
from .views import DocumentUploadView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
]


# Summary for phase 3:
    # Sets up the URL route for document uploads, linking to the DocumentUploadView.
    # backend/urls.py will include this file to integrate document routes into the main app.
