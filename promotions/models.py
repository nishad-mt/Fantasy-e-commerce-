from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Promotion(models.Model):

    PROMO_TYPE_CHOICES = (
        ("FIRST_ORDER", "First Order"),
        ("AUTO", "Auto Applied"),
        ("COUPON", "Coupon Code"),
    )

    name = models.CharField(max_length=100)

    promo_type = models.CharField(max_length=20,choices=PROMO_TYPE_CHOICES)

    # Discount (ONLY one should be set)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2,null=True, blank=True)

    discount_amount = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)

    # Minimum cart value for AUTO / COUPON
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    # Coupon code (ONLY for COUPON type)
    code = models.CharField(
        max_length=20,
        unique=True,
        null=True, blank=True
    )

    # Optional cap for percentage discounts
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    # Control
    is_active = models.BooleanField(default=True)

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    # Usage rules
    one_time_per_user = models.BooleanField(default=False)

    # Priority for AUTO promos (higher = applied first)
    priority = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):

        if self.promo_type == "FIRST_ORDER" and self.is_active:
                qs = Promotion.objects.filter(
                    promo_type="FIRST_ORDER",
                    is_active=True
                )
                if self.pk:
                    qs = qs.exclude(pk=self.pk)

                if qs.exists():
                    raise ValidationError(
                        "Only one active FIRST_ORDER promotion is allowed."
                    )
                    
        # Discount validation
        if self.discount_percent and self.discount_amount:
            raise ValidationError(
                "Set either discount_percent or discount_amount, not both."
            )

        if not self.discount_percent and not self.discount_amount:
            raise ValidationError(
                "You must set a discount_percent or discount_amount."
            )

        # Coupon validation
        if self.promo_type == "COUPON" and not self.code:
            raise ValidationError(
                "Coupon code is required for COUPON promotions."
            )

        if self.promo_type != "COUPON" and self.code:
            raise ValidationError(
                "Coupon code should only be set for COUPON promotions."
            )

        # Time validation
        if self.valid_from and self.valid_to:
            if self.valid_from >= self.valid_to:
                raise ValidationError(
                    "valid_from must be earlier than valid_to."
                )

    def is_valid_now(self):
        now = timezone.now()

        if not self.is_active:
            return False

        if self.valid_from and now < self.valid_from:
            return False

        if self.valid_to and now > self.valid_to:
            return False

        return True

    def __str__(self):
        return self.name


class PromotionUsage(models.Model):
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE
    )
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.CASCADE
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "promotion")
        verbose_name = "Promotion Usage"
        verbose_name_plural = "Promotion Usages"

    def __str__(self):
        return f"{self.user} used {self.promotion}"
