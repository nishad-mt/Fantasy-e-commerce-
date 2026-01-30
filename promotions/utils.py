from decimal import Decimal
from django.utils import timezone
from promotions.models import Promotion, PromotionUsage
from order.models import Order

def calculate_best_discount(user, subtotal, order=None):

    now = timezone.now()
    best_discount = Decimal("0.00")
    best_promo = None

    promotions = Promotion.objects.filter(
        is_active=True
    )

    for promo in promotions:

        # ⛔ Skip expired promotions
        if promo.valid_from and promo.valid_from > now:
            continue
        if promo.valid_to and promo.valid_to < now:
            continue

        discount = Decimal("0.00")

        # 🎉 FIRST ORDER
        if promo.promo_type == "FIRST_ORDER":

            has_completed_order = Order.objects.filter(
                user=user,
                status__in=["CONFIRMED", "DELIVERED"]
            ).exists()

            already_used = PromotionUsage.objects.filter(
                user=user,
                promotion=promo
            ).exists()

            if has_completed_order or already_used:
                continue

            discount = _calculate_discount_value(promo, subtotal)

        # 🔥 AUTO OFFER
        elif promo.promo_type == "AUTO":

            if promo.min_order_amount and subtotal < promo.min_order_amount:
                continue

            discount = _calculate_discount_value(promo, subtotal)

        # 🎟 COUPON → handled separately (manual entry)
        elif promo.promo_type == "COUPON":
            continue

        if discount > best_discount:
            best_discount = discount
            best_promo = promo

    return best_discount, best_promo
