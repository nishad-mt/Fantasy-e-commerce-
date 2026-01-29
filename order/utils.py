from decimal import Decimal
from .models import Order

def calculate_best_discount(user, subtotal, order):
    discount = Decimal("0.00")
    discount_type = None

    # Coupon has highest priority
    if order.discount_type == "COUPON" and order.discount_amount > 0:
        return order.discount_amount, "COUPON"

    is_first_order = not Order.objects.filter(
        user=user,
        status__in=["CONFIRMED", "DELIVERED"]
    ).exists()

    if is_first_order:
        discount = (Decimal("10") / Decimal("100")) * subtotal
        discount_type = "FIRST_ORDER"

    elif subtotal >= Decimal("1000"):
        discount = (Decimal("10") / Decimal("100")) * subtotal
        discount_type = "AUTO"

    discount = min(discount, subtotal)
    return discount, discount_type
