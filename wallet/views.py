from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Wallet

@login_required
def wallet(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.order_by("-created_at")

    return render(request, "wallet_detail.html", {
        "wallet": wallet,
        "transactions": transactions,
    })
