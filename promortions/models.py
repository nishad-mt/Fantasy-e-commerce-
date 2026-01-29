from django.db import models
from django.conf import settings
from django.utils import timezone


class Coupon(models.Model):
    code = models.CharField(max_length=30,unique=True,help_text="User enters this code manually")

    DISCOUNT_TYPE_CHOICES = (
        ("FLAT", "Flat Amount"),
        ("PERCENT", "Percentage"),
    )
    discount_type = models.CharField(max_length=10,choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10,decimal_places=2,help_text="Flat amount or percentage value")
    min_order_amount = models.DecimalField(max_digits=10,decimal_places=2,default=0,help_text="Minimum cart value required")
    max_discount_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True,help_text="Cap for percentage discounts")

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid_now(self):
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_to
        )

    def __str__(self):
        return self.code

class CouponUsage(models.Model):
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="usages"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    order = models.OneToOneField(
        "order.Order",
        on_delete=models.CASCADE
    )

    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("coupon", "user")
        indexes = [
            models.Index(fields=["coupon", "user"]),
        ]

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.email}"
