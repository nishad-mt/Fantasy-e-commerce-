from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, UserProfile



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
