from django import forms
from django.contrib.auth import authenticate

class LoginForm(forms.Form):
    email = forms.EmailField( widget=forms.EmailInput(attrs={
            'class': 'w-full mt-1 px-4 py-3 rounded-lg bg-white/15 border border-gray-400 outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-300',
            'placeholder': 'admin@example.com'
        }))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full mt-1 px-4 py-3 rounded-lg bg-white/15 border border-gray-400 outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-300',
            'placeholder': 'Enter password'
        })
    )


    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        user = authenticate(email=email, password=password)

        if not user:
            raise forms.ValidationError("Invalid credentials")

        cleaned_data['user'] = user
        return cleaned_data
