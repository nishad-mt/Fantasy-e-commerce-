from decimal import Decimal
from django.utils import timezone
from promotions.models import Promotion, PromotionUsage
from order.models import Order


def calculate_best_discount(user, subtotal, order=None):
    """
    Single source of truth for ALL promotion validations.
    Returns:
        (discount_amount, discount_type, applied_promotion)
    """

    now = timezone.now()

    best_discount = Decimal("0.00")
    best_type = None
    applied_promo = None

    # =====================================================
    # 1️⃣ FIRST ORDER PROMO
    # =====================================================
    first_order_promo = Promotion.objects.filter(
        promo_type="FIRST_ORDER",
        is_active=True,
    ).first()

    if first_order_promo:
        # validity check
        if (
            (first_order_promo.valid_from and now < first_order_promo.valid_from) or
            (first_order_promo.valid_to and now >= first_order_promo.valid_to)
        ):
            pass
        else:
            # user must have no successful orders
            already_ordered = Order.objects.filter(
                user=user,
                status__in=["CONFIRMED", "PACKED", "DELIVERED"]
            ).exists()

            if not already_ordered:
                if (
                    first_order_promo.min_order_amount and
                    subtotal < first_order_promo.min_order_amount
                ):
                    pass
                else:
                    if first_order_promo.discount_percent:
                        discount = subtotal * first_order_promo.discount_percent / 100
                    else:
                        discount = first_order_promo.discount_amount

                    if first_order_promo.max_discount_amount:
                        discount = min(discount, first_order_promo.max_discount_amount)

                    if discount > best_discount:
                        best_discount = discount
                        best_type = "FIRST_ORDER"
                        applied_promo = first_order_promo

    # =====================================================
    # 2️⃣ AUTO PROMOS (priority-based)
    # =====================================================
    auto_promos = Promotion.objects.filter(
        promo_type="AUTO",
        is_active=True,
    ).order_by("-priority")

    for promo in auto_promos:
        # validity checks
        if promo.valid_from and now < promo.valid_from:
            continue
        if promo.valid_to and now >= promo.valid_to:
            continue
        if promo.min_order_amount and subtotal < promo.min_order_amount:
            continue

        if promo.discount_percent:
            discount = subtotal * promo.discount_percent / 100
        else:
            discount = promo.discount_amount

        if promo.max_discount_amount:
            discount = min(discount, promo.max_discount_amount)

        if discount > best_discount:
            best_discount = discount
            best_type = "AUTO"
            applied_promo = promo

    # =====================================================
    # 3️⃣ COUPON PROMO (only if applied to order)
    # =====================================================
    if order and order.coupon:
        promo = order.coupon

        if not promo.is_active:
            pass
        elif promo.valid_from and now < promo.valid_from:
            pass
        elif promo.valid_to and now >= promo.valid_to:
            pass
        elif promo.min_order_amount and subtotal < promo.min_order_amount:
            pass
        elif promo.one_time_per_user and PromotionUsage.objects.filter(
            user=user,
            promotion=promo
        ).exists():
            pass
        else:
            if promo.discount_percent:
                discount = subtotal * promo.discount_percent / 100
            else:
                discount = promo.discount_amount

            if promo.max_discount_amount:
                discount = min(discount, promo.max_discount_amount)

            if discount > best_discount:
                best_discount = discount
                best_type = "COUPON"
                applied_promo = promo

    # =====================================================
    # FINAL SAFE RETURN
    # =====================================================
    return (
        best_discount if best_discount > 0 else Decimal("0.00"),
        best_type,
        applied_promo
    )
