from django.db import models
from django.conf import settings
from products.models import SizeVariant
from addresses.models import Address
import uuid

class Order(models.Model):
    address = models.ForeignKey(
        "addresses.Address",
        on_delete=models.PROTECT,
    )
    STATUS_CHOICES = [
        ("PENDING", "Pending Payment"),
        ("PAID", "Paid"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    delivery_date = models.DateField()

    def __str__(self):
        return str(self.order_id)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(SizeVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot price

    def __str__(self):
        return f"{self.variant.product.name} ({self.variant.size_name})"
