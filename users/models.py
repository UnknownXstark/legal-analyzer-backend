from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(AbstractUser):
    ROLE_CHOICES = [
        ('individual', 'Individual'),
        ('lawyer', 'Lawyer'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='individual')

    def __str__(self):
        return f"{self.username} ({self.role})"

# This gives us three distinct user types:
    # Individual → Can upload, analyze, and view only their own documents.
    # Lawyer → Can view documents from their clients.
    # Admin → Can view all documents across the platform.

class ClientAssignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    lawyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="client_requests"
    )
    client = models.OneToOneField(
        User,   # One client → one lawyer
        on_delete=models.CASCADE,
        related_name="lawyer_assignment"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lawyer', 'client')

    def __str__(self):
        return f"{self.client.email} → {self.lawyer.email} ({self.status})"
    

class AssignmentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    lawyer = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='sent_assignment_requests'
    )
    client = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='received_assignment_requests'
    )
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lawyer', 'client')  # prevent duplicate requests
        ordering = ['-created_at']

    def __str__(self):
        return f"Request: {self.lawyer} -> {self.client} ({self.status})"