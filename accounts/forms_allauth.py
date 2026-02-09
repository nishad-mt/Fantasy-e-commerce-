from allauth.account.forms import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser

class AllauthSignupForm(SignupForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Style existing allauth fields instead of redefining them
        self.fields["email"].widget = forms.EmailInput(attrs={
            "class": "input-box",
            "placeholder": "Email Address",
            "required": True,
        })

        self.fields["password1"].widget = forms.PasswordInput(attrs={
            "class": "input-box password-field",
            "placeholder": "Create Password",
            "required": True,
        })

        self.fields["password2"].widget = forms.PasswordInput(attrs={
            "class": "input-box password-field",
            "placeholder": "Confirm Password",
            "required": True,
        })

    def clean_email(self):
        email = self.cleaned_data.get("email")

        blocked_domains = [
            "tempmail.com",
            "mailinator.com",
            "10minutemail.com",
        ]

        domain = email.split("@")[-1].lower()

        if domain in blocked_domains:
            raise ValidationError("Temporary email addresses are not allowed.")

        allowed_domains = [
            "gmail.com",
            "yahoo.com",
            "outlook.com",
            "icloud.com",
        ]

        if domain not in allowed_domains:
            raise ValidationError("Please use a valid email provider.")

        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")

        return email

