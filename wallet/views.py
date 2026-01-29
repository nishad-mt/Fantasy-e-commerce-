from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Wallet
from django.shortcuts import get_object_or_404
from accounts.decarators import admin_required


@login_required
def wallet(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.order_by("-created_at")

    return render(request, "wallet_detail.html", {
        "wallet": wallet,
        "transactions": transactions,
    })

@admin_required
@login_required
def admin_user_wallet_detail(request, user_id):
    wallet = get_object_or_404(
        Wallet.objects.select_related("user"),
        user__id=user_id
    )

    transactions = (
        wallet.transactions
        .select_related("order")
        .order_by("-created_at")
    )

    context = {
        "wallet": wallet,
        "transactions": transactions,
    }

    return render(request, "user_wallet_detail.html", context)
