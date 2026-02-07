from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, UserProfile
from django.core.exceptions import ValidationError

class CustomUserForm(UserCreationForm):
    
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'input-box',
            'placeholder': 'Your Name',
            'required': True,
        })
    )
    
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'input-box',
        'placeholder': 'Email Address',
        'required': True,
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'input-box',
        'placeholder': 'Create Password',
        'required': True,
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'input-box',
        'placeholder': 'Confirm Password',
        'required': True,
    }))

    class Meta:
        model = CustomUser
        fields = ['email', 'password1', 'password2']
    
    def clean_email(self):
            email = self.cleaned_data.get("email")

            # Block temporary/fake email providers
            blocked_domains = [
                "tempmail.com",
                "mailinator.com",
                "10minutemail.com",
            ]

            domain = email.split("@")[-1].lower()

            if domain in blocked_domains:
                raise ValidationError("Temporary email addresses are not allowed.")

            # Optional: allow only popular providers
            allowed_domains = [
                "gmail.com",
                "yahoo.com",
                "outlook.com",
                "icloud.com"
            ]

            if domain not in allowed_domains:
                raise ValidationError("Please use a valid email provider.")

            # Prevent duplicate signup
            if CustomUser.objects.filter(email=email).exists():
                raise ValidationError("An account with this email already exists.")

            return email

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "first_name",
            "last_name",
            "profile_img",
            "dob",
            "gender",
            "mobile_number",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }
