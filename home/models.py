from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ContactMessage(models.Model):
    CATEGORY_CHOICES = [
        ("order", "Order / Delivery"),
        ("payment", "Payment / Refund"),
        ("product", "Product Inquiry"),
        ("account", "Account / Login"),
        ("feedback", "Feedback"),
        ("other", "Other"),
    ]
    user = models.ForeignKey(User,on_delete=models.SET_NULL, null=True,blank=True)
    name = models.CharField(max_length=20)
    number = models.CharField(max_length=10)
    category = models.CharField(max_length=50,choices=CATEGORY_CHOICES,blank=True,null=True,help_text="Assigned by admin")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.category or 'uncategorized'}"

class SiteContact(models.Model):
    address = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=10)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email