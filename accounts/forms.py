from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser, UserProfile

class CustomUserForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "input-box",
            "placeholder": "Password",
            "required": True,
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "input-box",
            "placeholder": "Confirm Password",
            "required": True,
        })
    )

    class Meta:
        model = CustomUser
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        domain = email.split("@")[-1].lower()

        blocked_domains = ["tempmail.com", "mailinator.com", "10minutemail.com"]
        allowed_domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]

        if domain in blocked_domains:
            raise ValidationError("Temporary email addresses are not allowed.")

        if domain not in allowed_domains:
            raise ValidationError("Please use a valid email provider.")

        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")

        return cleaned_data

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'dob', 'gender', 'mobile_number', 'profile_img']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'profile_img': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'input-box'})

    def clean_profile_img(self):
        image = self.cleaned_data.get('profile_img')
        if not image:
            return image

        # If it's not a newly uploaded file (string path), skip validation
        if not hasattr(image, 'content_type'):
            return image

        # Check content type
        content_type = image.content_type
        if content_type == 'image/gif':
             raise ValidationError("GIF images are not allowed.")
        if not content_type in ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']:
             raise ValidationError("Only JPG, JPEG, and PNG images are allowed.")
             
        # Check file extension
        name = image.name.lower()
        if name.endswith('.gif'):
             raise ValidationError("GIF images are not allowed.")
        if not any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
             raise ValidationError("Only JPG, JPEG, and PNG images are allowed.")

        return image
