from django import forms
from .models import SiteContact
import re

class SiteContactForm(forms.ModelForm):

    class Meta:
        model = SiteContact
        fields = ["address", "contact_number", "email"]

    def clean_address(self):
        address = self.cleaned_data.get("address", "").strip()
        if len(address) < 5:
            raise forms.ValidationError("Address is too short.")
        return address

    def clean_contact_number(self):
        number = self.cleaned_data.get("contact_number", "").strip()

        # allow +, digits, spaces
        if not re.match(r'^[+0-9 ]+$', number):
            raise forms.ValidationError("Phone number can contain only digits, spaces and +.")

        digits = re.sub(r'\D', '', number)
        if len(digits) < 10:
            raise forms.ValidationError("Phone number must have at least 10 digits.")

        return number

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise forms.ValidationError("Email is required.")
        return email
