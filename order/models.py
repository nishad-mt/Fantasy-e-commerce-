from django.db import models
from django.conf import settings
from products.models import SizeVariant
import uuid

class Order(models.Model):
    address = models.ForeignKey(
        "addresses.Address",
        on_delete=models.PROTECT,
    )
    PAYMENT_METHOD_CHOICES = [
        ("COD", "Cash on Delivery"),
        ("ONLINE", "Online Payment")
    ]
    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "success"),
        ("FAILED", "Failed"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("PREPARING", "Preparing"),
        ("PACKED", "packed"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]
    CANCEL_REASONS = [
        ("CHANGED_MIND", "Changed my mind"),
        ("WRONG_ADDRESS", "Wrong delivery address"),
        ("FOUND_CHEAPER", "Found a better price elsewhere"),
        ("ORDERED_BY_MISTAKE", "Ordered by mistake"),
        ("DELIVERY_DELAY", "Delivery is taking too long"),
        ("OTHER", "Other"),
    ]

    cancel_reason = models.CharField(max_length=50,choices=CANCEL_REASONS,blank=True,null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order_items_total = models.DecimalField(max_digits=10, decimal_places=2, null=True,blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default="PENDING"
    )


    def __str__(self):
        return str(self.order_id)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(SizeVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot price
    
    class Meta:
        unique_together = ("order", "variant")

    def __str__(self):
        return f"{self.variant.product.name} ({self.variant.size_name})"

