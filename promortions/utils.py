from decimal import Decimal
from django.utils import timezone
from promortions.models import Coupon, CouponUsage


def calculate_coupon_discount(coupon, subtotal):
    if coupon.discount_type == "FLAT":
        discount = coupon.discount_value
    else:
        discount = (coupon.discount_value / Decimal("100")) * subtotal

    if coupon.max_discount_amount:
        discount = min(discount, coupon.max_discount_amount)

    return min(discount, subtotal)


def user_used_coupon(user, coupon):
    return CouponUsage.objects.filter(user=user, coupon=coupon).exists()
