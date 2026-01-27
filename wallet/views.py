from django.contrib.auth.decorators import login_required
from .models import Wallet
from django.shortcuts import render


@login_required
def wallet_detail(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    return render(request, "wallet_detail.html", {
        "wallet": wallet
    })

@login_required
def wallet_transactions(request):
    wallet = Wallet.objects.get(user=request.user)
    transactions = wallet.transactions.order_by("-created_at")

    return render(request, "wallet_transactions.html", {
        "wallet": wallet,
        "transactions": transactions
    })
