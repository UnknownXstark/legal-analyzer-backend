from django.urls import path
from .views import DocumentListView, DocumentUploadView, DocumentDetailView, DocumentAnalysisView, DocumentReportView, DocumentDeleteView, IndividualDashboardView, AdminDashboardView, LawyerDashboardView, LawyerDashboardAnalyticsView, AdminDashboardAnalyticsView, DocumentDownloadView, DocumentCommentsView, DocumentCommentDeleteView, DocumentVersionListView, DocumentVersionDetailView, ShareDocumentView, AcceptSharedDocumentView, DeclineSharedDocumentView, LawyerSharedDocumentsList, ClientSharedDocumentsList

urlpatterns = [
    path('', DocumentListView.as_view(), name='document-list'),
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('<int:pk>/',  DocumentDetailView.as_view(), name='document-detail'),
    path('<int:pk>/analyze/', DocumentAnalysisView.as_view(), name='document-analyze'),
    path('<int:pk>/report/', DocumentReportView.as_view(), name='document-report'),
    path("<int:pk>/download/", DocumentDownloadView.as_view(), name="document-download"),
    path('<int:pk>/delete/', DocumentDeleteView.as_view(), name='document-delete'),
     path('<int:pk>/comments/', DocumentCommentsView.as_view(), name='document-comments'),
    path('comments/<int:comment_id>/', DocumentCommentDeleteView.as_view(), name='document-comment-delete'),
    path('<int:pk>/versions/', DocumentVersionListView.as_view(), name='document-versions-list'),
    path('versions/<int:version_id>/', DocumentVersionDetailView.as_view(), name='document-version-detail'),
    path("share/", ShareDocumentView.as_view(), name="share-document"),
    path("share/<int:share_id>/accept/", AcceptSharedDocumentView.as_view(), name="accept-shared-document"),
    path("share/<int:share_id>/decline/", DeclineSharedDocumentView.as_view(), name="decline-shared-document"),
    path("shared/by-me/", LawyerSharedDocumentsList.as_view(), name="lawyer-shared-documents"),
    path("shared/with-me/", ClientSharedDocumentsList.as_view(), name="client-shared-documents"),

    # Dashboards
    path('dashboard/individual/', IndividualDashboardView.as_view(), name='individual-dashboard'),
    path('dashboard/lawyer/', LawyerDashboardView.as_view(), name='lawyer-dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path("lawyer/analytics/", LawyerDashboardAnalyticsView.as_view()),
     path("admin/analytics/", AdminDashboardAnalyticsView.as_view(), name="admin-analytics"),
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

# Summary for phase 7:
    # Added the routes for each dashboard.