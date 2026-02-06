from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import get_object_or_404

from .forms import PromotionForm
from .models import Promotion, PromotionUsage
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from order.models import Order
from decimal import Decimal
from .utils import calculate_best_discount
from django.db import transaction
from django.views.decorators.cache import never_cache



def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
@never_cache
def create_promotion(request):
    if request.method == "POST":
        form = PromotionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Promotion created successfully.")
            return redirect("promotion_list")
    else:
        form = PromotionForm()

    return render(
        request,
        "create_promotion.html",
        {
            "form": form,
            "is_edit": False,
        }
    )

@login_required
@user_passes_test(is_admin)
@never_cache
def edit_promotion(request, promotion_id):
    promotion = get_object_or_404(Promotion, id=promotion_id)

    if request.method == "POST":
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            messages.success(request, "Promotion updated successfully.")
            return redirect("promotion_list")
    else:
        form = PromotionForm(instance=promotion)

    return render(
        request,
        "create_promotion.html",
        {
            "form": form,
            "is_edit": True,
            "promotion": promotion,
        }
    )

@login_required
@user_passes_test(is_admin)
@never_cache
def promotion_list(request):
    now = timezone.now()

    promotions = Promotion.objects.all().order_by("-created_at")

    # 🔍 SEARCH
    search = request.GET.get("search")
    if search:
       promotions = promotions.filter(Q(name__icontains=search) | Q(code__icontains=search))

    # 🎯 FILTERS
    promo_type = request.GET.get("type")
    status = request.GET.get("status")

    if promo_type:
        promotions = promotions.filter(promo_type=promo_type)

    if status == "active":
        promotions = promotions.filter(
            is_active=True
        ).filter(
            Q(valid_from__isnull=True) | Q(valid_from__lte=now),
            Q(valid_to__isnull=True) | Q(valid_to__gt=now),
        )

    elif status == "expired":
        promotions = promotions.filter(
            is_active=True,
            valid_to__isnull=False,
            valid_to__lte=now
        )


    elif status == "inactive":
        promotions = promotions.filter(is_active=False)

    elif status == "upcoming":
        promotions = promotions.filter(
            is_active=True,
            valid_from__isnull=False,
            valid_from__gt=now
        )

    # 📊 COUNTS (ALWAYS from full table)
    total_count = Promotion.objects.count()

    active_count = Promotion.objects.filter(
        is_active=True
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_to__isnull=True) | Q(valid_to__gt=now),
    ).count()

    expired_count = Promotion.objects.filter(
        valid_to__isnull=False,
        valid_to__lte=now
    ).count()

    upcoming_count = Promotion.objects.filter(
        is_active=True,
        valid_from__isnull=False,
        valid_from__gt=now
    ).count()

    return render(
        request,
        "offers_adm.html",
        {
            "promotions": promotions,
            "total_count": total_count,
            "active_count": active_count,
            "expired_count": expired_count,
            "upcoming_count": upcoming_count,
            "promo_types": Promotion.PROMO_TYPE_CHOICES,
        }
    )

@login_required
@user_passes_test(is_admin)
@never_cache
def delete_promotion(request, promotion_id):
    promotion = get_object_or_404(Promotion, id=promotion_id)

    if request.method == "POST":
        promotion.delete()
        messages.success(request, "Promotion deleted successfully.")
        return redirect("promotion_list")

    messages.error(request, "Invalid request.")
    return redirect("promotion_list")

@login_required
@never_cache
def apply_coupon(request):
    if request.method != "POST":
        return redirect("cart:cart")

    code = request.POST.get("coupon_code", "").strip().upper()
    order_id = request.POST.get("order_id")

    # 🔑 Must be DRAFT order
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status="DRAFT"
    )

    # ❌ NEVER use get_object_or_404 for coupons
    coupon = Promotion.objects.filter(
        promo_type="COUPON",
        code=code,
        is_active=True
    ).first()

    if not coupon:
        messages.error(request, "Invalid or inactive coupon.")
        return redirect("pay_order", order_id=order.order_id)

    now = timezone.now()

    # ⏳ Validity window check
    if coupon.valid_from and now < coupon.valid_from:
        messages.error(request, "This coupon is not active yet.")
        return redirect("pay_order", order_id=order.order_id)

    if coupon.valid_to and now >= coupon.valid_to:
        messages.error(request, "This coupon has expired.")
        return redirect("pay_order", order_id=order.order_id)

    # 🔥 Calculate subtotal
    subtotal = sum(
        item.variant.price * item.quantity
        for item in order.items.all()
    )

    # 💰 Minimum order value
    if coupon.min_order_amount and subtotal < coupon.min_order_amount:
        messages.error(
            request,
            f"Minimum order value ₹{coupon.min_order_amount} required."
        )
        return redirect("pay_order", order_id=order.order_id)

    # 🔒 One-time per user
    if coupon.one_time_per_user and PromotionUsage.objects.filter(
        user=request.user,
        promotion=coupon
    ).exists():
        messages.error(request, "You already used this coupon.")
        return redirect("pay_order", order_id=order.order_id)

    # ✅ Attach coupon to DRAFT order (preview only)
    order.coupon = coupon
    order.discount_type = "COUPON"
    order.save(update_fields=["coupon", "discount_type"])

    messages.success(request, "Coupon applied successfully.")
    return redirect("pay_order", order_id=order.order_id)

def offers(request):
    now = timezone.now()

    offers = Promotion.objects.filter(
        is_active=True
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_to__isnull=True) | Q(valid_to__gt=now),
    ).order_by("-created_at")

    return render(request, "offers.html", {
        "offers": offers
    })