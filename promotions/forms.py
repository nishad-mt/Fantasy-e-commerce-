from django import forms
from .models import Promotion


class PromotionForm(forms.ModelForm):

    class Meta:
        model = Promotion
        fields = [
            "name",
            "promo_type",
            "discount_percent",
            "discount_amount",
            "max_discount_amount",
            "min_order_amount",
            "code",
            "is_active",
            "valid_from",
            "valid_to",
            "one_time_per_user",
            "priority",
        ]

        widgets = {
            "valid_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "valid_to": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        promo_type = cleaned_data.get("promo_type")
        code = cleaned_data.get("code")
        discount_percent = cleaned_data.get("discount_percent")
        discount_amount = cleaned_data.get("discount_amount")

        if discount_percent and discount_amount:
            raise forms.ValidationError(
                "Choose either percentage or fixed discount, not both."
            )

        if promo_type == "COUPON" and not code:
            raise forms.ValidationError(
                "Coupon code is required for coupon promotions."
            )
        return cleaned_data
    
    def clean_code(self):
        code = self.cleaned_data.get("code")
        if code and not code.isalnum():
            raise forms.ValidationError(
                "Coupon code must contain only letters and numbers."
            )
        return code.upper()
