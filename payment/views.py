from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

import razorpay
import hmac
import json
import hashlib
import razorpay

from payment.models import Payment
from order.models import Order
from cart.models import Cart

@csrf_protect
@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    order_id = request.POST.get("order_id")
    if not order_id:
        return HttpResponseBadRequest("Order ID missing")

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    order.payment_method = "ONLINE"
    order.payment_status = "PENDING"
    order.save()

    amount_paise = int(order.total_amount * 100)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1
    })

    Payment.objects.create(
        user=request.user,
        order=order,
        razorpay_order_id=razorpay_order["id"],
        amount=order.total_amount,
        status="CREATED"
    )

    return JsonResponse({
        "razorpay_order_id": razorpay_order["id"],
        "key": settings.RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "currency": "INR",
    })


@csrf_exempt
def razorpay_webhook(request):
    payload = request.body.decode("utf-8")  
    received_signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE")
    
    if not received_signature:
        return HttpResponse(status=400)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_webhook_signature(
            payload,
            received_signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        return HttpResponse(status=400)

    data = json.loads(payload)

    if data.get("event") == "payment.captured":
        entity = data["payload"]["payment"]["entity"]

        razorpay_order_id = entity["order_id"]
        razorpay_payment_id = entity["id"]
        method = entity["method"]

        payment = Payment.objects.select_related("order").filter(
            razorpay_order_id=razorpay_order_id
        ).first()

        if payment and payment.status != "SUCCESS":
            payment.razorpay_payment_id = razorpay_payment_id
            payment.gateway_method = method
            payment.status = "SUCCESS"
            payment.save()

            order = payment.order
            order.payment_status = "SUCCESS"
            order.status = "CONFIRMED"
            order.paid_at = timezone.now()
            order.save()

            cart = Cart.objects.filter(user=order.user).first()
            if cart:
                cart.items.all().delete()

    return HttpResponse(status=200)

def success(request):
    return render(request, "success.html")
