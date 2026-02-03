from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from promotions.models import PromotionUsage

import razorpay
import hmac
import json
import hashlib
import razorpay

from payments.models import Payment
from order.models import Order
from cart.models import CartItem
from django.db import transaction
from django.views.decorators.cache import never_cache
from decimal import Decimal

@csrf_protect
@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    order_id = request.POST.get("order_id")
    if not order_id:
        return HttpResponseBadRequest("Order ID missing")

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status="PENDING_PAYMENT",
        payment_status="PENDING"
    )

    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "user": request.user,
            "amount": order.total_amount,
            "status": "CREATED"
        }
    )

    if created:
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        razorpay_order = client.order.create({
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        payment.razorpay_order_id = razorpay_order["id"]
        payment.save()

    return JsonResponse({
        "razorpay_order_id": payment.razorpay_order_id,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": int(payment.amount * 100),
        "currency": "INR",
    })


@csrf_exempt
@transaction.atomic
def razorpay_webhook(request):
    payload = request.body.decode()
    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE")

    if not signature:
        return HttpResponse(status=400)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_webhook_signature(
            payload,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        return HttpResponse(status=400)

    data = json.loads(payload)

    if data.get("event") != "payment.captured":
        return HttpResponse(status=200)

    entity = data["payload"]["payment"]["entity"]
    razorpay_order_id = entity["order_id"]
    paid_amount = entity["amount"] / Decimal("100")

    payment = Payment.objects.select_related("order").filter(
        razorpay_order_id=razorpay_order_id
    ).first()

    if not payment or payment.status == "SUCCESS":
        return HttpResponse(status=200)

    if paid_amount != payment.amount:
        return HttpResponse(status=400)

    order = payment.order

    payment.razorpay_payment_id = entity["id"]
    payment.gateway_method = entity["method"]
    payment.status = "SUCCESS"
    payment.save()

    order.payment_status = "SUCCESS"
    order.status = "CONFIRMED"
    order.paid_at = timezone.now()
    order.save()

    # 🔒 Lock coupon ONLY here
    if order.discount_type == "COUPON" and order.coupon:
        PromotionUsage.objects.get_or_create(
            user=order.user,
            promotion=order.coupon,
            order=order
        )

    # 🧹 Clear cart
    CartItem.objects.filter(cart__user=order.user).delete()

    return HttpResponse(status=200)

@never_cache
def success(request):
    return render(request, "success.html")

#Razorpay (or JS webhook-style requests) does NOT automatically send Django’s CSRF token.
#So Django would block the request unless you exempt it.
@csrf_exempt
@login_required
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "invalid"}, status=400)

    data = json.loads(request.body)

    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")
    order_id = data.get("order_id")

    # 🔑 Verify signature
    generated_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if generated_signature != razorpay_signature:
        return JsonResponse({"status": "failed"})

    payment = Payment.objects.select_related("order").get(
        razorpay_order_id=razorpay_order_id
    )

    order = payment.order

    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = "SUCCESS"
    payment.save()

    order.payment_status = "SUCCESS"
    order.status = "CONFIRMED"
    order.paid_at = timezone.now()
    order.save()

    CartItem.objects.filter(cart__user=order.user).delete()

    return JsonResponse({"status": "success"})