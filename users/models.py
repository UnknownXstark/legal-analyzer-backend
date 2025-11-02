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