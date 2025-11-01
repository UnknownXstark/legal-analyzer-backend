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
