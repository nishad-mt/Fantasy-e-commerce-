from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ContactMessage(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("replied", "Replied"),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=20)
    number = models.CharField(max_length=16)
    category = models.CharField(max_length=50, blank=True, null=True)
    message = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

class SiteContact(models.Model):
    address = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=16)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email