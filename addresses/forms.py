from django import forms
from .models import Address
import re

class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = ["name", "phone", "street", "city", "state", "pincode", "is_default"]
        widgets = {
            "street": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 3:
            raise forms.ValidationError("Name is too short.")

        if not re.match(r"^[A-Za-z\s]+$", name):
            raise forms.ValidationError("Name should contain only letters.")

        return name

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        if not phone.isdigit():
            raise forms.ValidationError("Phone must contain only numbers.")

        if len(phone) != 10:
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")

        return phone

    def clean_street(self):
        street = self.cleaned_data["street"].strip()

        if len(street) < 10:
            raise forms.ValidationError("Please enter full address (house, street, area).")

        return street

    def clean_city(self):
        city = self.cleaned_data["city"].strip()

        if not re.match(r"^[A-Za-z\s]+$", city):
            raise forms.ValidationError("City should contain only letters.")

        return city

    def clean_state(self):
        state = self.cleaned_data["state"].strip()

        if not re.match(r"^[A-Za-z\s]+$", state):
            raise forms.ValidationError("State should contain only letters.")

        return state

    def clean_pincode(self):
        pin = self.cleaned_data["pincode"].strip()

        if not pin.isdigit():
            raise forms.ValidationError("Pincode must be numeric.")

        if len(pin) != 6:
            raise forms.ValidationError("Enter a valid 6-digit pincode.")

        return pin

    def clean(self):
        data = super().clean()

        text = f"{data.get('street','')} {data.get('city','')} {data.get('state','')}".lower()

        bad_words = ["test", "asdf", "dummy", "xxx", "abc"]
        for word in bad_words:
            if word in text:
                raise forms.ValidationError("Please enter a real delivery address.")

        return data
