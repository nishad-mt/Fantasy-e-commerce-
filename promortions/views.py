from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from promortions.models import Coupon
from promortions.utils import calculate_coupon_discount, user_used_coupon
from order.models import Order


@login_required
def apply_coupon(request):
    code = request.POST.get("code", "").upper()
    order_id = request.POST.get("order_id")

    order = Order.objects.get(order_id=order_id, user=request.user)

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return JsonResponse({"error": "Invalid coupon code"}, status=400)

    if not coupon.is_valid_now():
        return JsonResponse({"error": "Coupon expired or inactive"}, status=400)

    if user_used_coupon(request.user, coupon):
        return JsonResponse({"error": "You already used this coupon"}, status=400)

    if order.order_items_total < coupon.min_order_amount:
        return JsonResponse({
            "error": f"Minimum order ₹{coupon.min_order_amount}"
        }, status=400)

    discount = calculate_coupon_discount(coupon, order.order_items_total)

    # Temporarily attach to order
    order.discount_amount = discount
    order.discount_type = "COUPON"
    order.coupon = coupon
    order.total_amount -= discount
    order.save()

    return JsonResponse({
        "success": True,
        "discount": float(discount),
        "new_total": float(order.total_amount)
    })
