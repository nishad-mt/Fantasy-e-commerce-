from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import get_object_or_404

from .forms import PromotionForm
from .models import Promotion
from django.utils import timezone
from django.db.models import Q



def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
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
def promotion_list(request):
    now = timezone.now()

    promotions = Promotion.objects.all().order_by("-created_at")

    # 🔍 SEARCH
    search = request.GET.get("search")
    if search:
        promotions = promotions.filter(name__icontains=search)

    # 🎯 FILTERS
    promo_type = request.GET.get("type")
    status = request.GET.get("status")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if promo_type:
        promotions = promotions.filter(promo_type=promo_type)

    if status == "active":
        promotions = promotions.filter(
            is_active=True
        ).filter(
            Q(valid_from__lte=now) | Q(valid_from__isnull=True),
            Q(valid_to__gte=now) | Q(valid_to__isnull=True)
        )

    elif status == "expired":
        promotions = promotions.filter(valid_to__lt=now)

    elif status == "inactive":
        promotions = promotions.filter(is_active=False)

    if start_date:
        promotions = promotions.filter(created_at__date__gte=start_date)

    if end_date:
        promotions = promotions.filter(created_at__date__lte=end_date)

    total_count = Promotion.objects.count()

    active_count = Promotion.objects.filter(
        is_active=True
    ).filter(
        Q(valid_from__lte=now) | Q(valid_from__isnull=True),
        Q(valid_to__gte=now) | Q(valid_to__isnull=True)
    ).count()

    expired_count = Promotion.objects.filter(
        valid_to__lt=now
    ).count()

    context = {
        "promotions": promotions,
        "total_count": total_count,
        "active_count": active_count,
        "expired_count": expired_count,
        "promo_types": Promotion.PROMO_TYPE_CHOICES,
    }

    return render(
        request,
        "offers_adm.html",
        context
    )

@login_required
@user_passes_test(is_admin)
def delete_promotion(request, promotion_id):
    promotion = get_object_or_404(Promotion, id=promotion_id)

    if request.method == "POST":
        promotion.delete()
        messages.success(request, "Promotion deleted successfully.")
        return redirect("promotion_list")

    messages.error(request, "Invalid request.")
    return redirect("promotion_list")