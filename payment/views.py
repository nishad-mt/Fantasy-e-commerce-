from django.shortcuts import render
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import hmac
import json
import hashlib
from django.http import HttpResponse
from payment.models import Payment

@csrf_exempt
def create_razorpay_order(request):
    if request.method == "POST":
        amount = int(float(request.POST.get("amount")) * 100)  # ₹ → paise

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })

        return JsonResponse({
            "order_id": order["id"],
            "key": settings.RAZORPAY_KEY_ID,
            "amount": amount
        })


def test_payment(request):
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    order = client.order.create({
        "amount": 100,        
        "currency": "INR",
        "payment_capture": 1
    })

    return render(request, "test_payment.html", {
        "order_id": order["id"],
        "key": settings.RAZORPAY_KEY_ID,
        "amount": 100
    })

def success(request):
    return render(request,"success.html")


@csrf_exempt
def razorpay_webhook(request):
    payload = request.body
    received_signature = request.headers.get("X-Razorpay-Signature")

    # Verify webhook signature
    expected_signature = hmac.new(
        bytes(settings.RAZORPAY_WEBHOOK_SECRET, "utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(received_signature, expected_signature):
        return HttpResponse(status=400)

    data = json.loads(payload)

    if data.get("event") == "payment.captured":
        payment_entity = data["payload"]["payment"]["entity"]

        razorpay_payment_id = payment_entity["id"]
        method = payment_entity["method"]  # 🔥 REAL METHOD

        # Update your Payment record
        payment = Payment.objects.filter(txn_id=razorpay_payment_id).first()
        if payment:
            payment.gateway_method = method
            payment.save()

    return HttpResponse(status=200)