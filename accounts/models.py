from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin
from django.utils import timezone
import uuid
from .managers import CustomUserManager
from django.conf import settings

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(unique=True)

    joined_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    is_email_vfd = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    auth_provider = models.CharField(max_length=50, default="email", blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class UserProfile(models.Model):
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                 related_name="profile")
    
    first_name = models.CharField(max_length=20,blank=True ,null=True)
    last_name = models.CharField(max_length=20,blank=True ,null=True)
    profile_img = models.ImageField(upload_to="profiles/",blank=True,null=True,verbose_name="Profile Image")
    dob = models.DateField(blank=True, null=True)
    GENDER_CHOICES = (
        ("male","Male"),    #This is what Django saves internally in your model field.
        ("female","Female"), #This is what the user sees in the dropdown.
    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)  
    mobile_number = models.CharField(max_length=15,blank=True,null=True)

    def __str__(self):
        return str(self.user)
