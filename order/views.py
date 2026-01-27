from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from cart.models import Cart
from .models import Order,OrderItem
from payment.models import Payment
from products.models import SizeVariant
from addresses.models import Address
from django.contrib import messages
from datetime import date,timedelta
from django.db import transaction
import uuid
import json
from django.db.models import Case, When, IntegerField,Value
from django.utils import timezone
from django.http import JsonResponse
import razorpay
from django.conf import settings
from wallet.models import WalletTransaction,Wallet


@login_required
def order(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related("items__variant__product")
        .annotate(
            status_priority=Case(
                When(status="PENDING", then=Value(1)),
                When(status="CONFIRMED", then=Value(2)),
                When(status="PACKED", then=Value(3)),
                When(status="DELIVERED", then=Value(4)),
                When(status="CANCELLED", then=Value(5)),
                default=Value(6),
                output_field=IntegerField(),
            )
        )
        .order_by("status_priority", "-created_at")
    )
    return render(request, "order.html", {
        "orders": orders,
    })
    
@login_required
def checkout(request):
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    
    delivery_date = date.today() + timedelta(days=3)

    return render(request, "checkout.html", {
        "addresses": addresses,
        "default_address": default_address,
        'delivery_date':delivery_date
    })

@login_required
def create_from_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("variant")

    if not items.exists():
        return redirect("cart:cart")

    order_items_total = Decimal("0.00")
    for item in items:
        order_items_total += item.variant.price * item.quantity

    delivery = Decimal("0.00") if order_items_total > 500 else Decimal("40.00")
    product_total = order_items_total
    total = order_items_total + delivery

    default_address = Address.objects.filter(
        user=request.user,
        is_default=True
    ).first()

    if not default_address:
        return redirect("checkout")

    delivery_date = date.today() + timedelta(days=3)

    order = Order.objects.create(
        user=request.user,
        address=default_address,
        order_items_total=product_total,
        total_amount=total,
        delivery_charge=delivery,
        delivery_date=delivery_date,
        status="PENDING"

    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.price
        )

    return redirect("pay_order", order_id=order.order_id)

@login_required
def pay_order(request, order_id):

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    return render(request, "checkout.html", {
        "order": order,
        "items": order.items.select_related("variant", "variant__product"),
        "addresses": addresses,
        "default_address": default_address
    })

def order_detail(request,order_id):
    order = get_object_or_404(Order,order_id=order_id,user=request.user)
    items = order.items.select_related('variant','variant__product')
    return render(request,"order_detail.html",{
        'order':order,
        'items':items
        }
                  )

@transaction.atomic
@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("variant")

    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart")

    order_id = request.POST.get("order_id")
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status="PENDING"
    )
    if not order or not order.address:
        messages.error(request, "Please select a delivery address.")
        return redirect("checkout")

    subtotal = sum(item.variant.price * item.quantity for item in items)
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")
    total = subtotal + delivery

    order.total_amount = total
    order.delivery_charge = delivery
    order.delivery_date = date.today() + timedelta(days=3)

    payment_method = request.POST.get("payment_method")

    if payment_method == "COD":
        order.payment_method = "COD"
        order.payment_status = "PENDING"
       
    else:
        messages.error(request, "Invalid payment method.")
        return redirect("checkout")

    order.save()

    if payment_method == "COD":
        cart.items.all().delete()


    return redirect("order_success", order_id=order.order_id)

@login_required
def select_address(request):
    if request.method == "POST":
        address_id = request.POST.get("address_id")

        order = Order.objects.filter(user=request.user, status="PENDING").first()
        if not order:
            return redirect("cart:cart")
        address = get_object_or_404(Address, id=address_id, user=request.user)

        order.address = address
        order.save()

    return redirect("checkout")

@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )
    return render(request, "order_success.html", {"order": order})

def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.select_related("variant", "variant__product")

    return render(
        request,
        "admin_order_detail.html",
        {
            "order": order,
            "items": items,
        },
    )
    
@login_required
@transaction.atomic
def cancel_order_request(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )

    if order.status not in ["PENDING", "CONFIRMED"]:
        messages.error(request, "This order cannot be cancelled.")
        return redirect("order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("cancel_reason")

        if not reason:
            messages.error(request, "Please select a cancellation reason.")
            return redirect("order_detail", order_id=order.order_id)

        # -------------------------
        # CANCEL ORDER
        # -------------------------
        order.status = "CANCELLED"
        order.cancel_reason = reason
        order.cancelled_at = timezone.now()

        # -------------------------
        # WALLET REFUND (ONLINE)
        # -------------------------
        if (
            order.payment_method == "ONLINE"
            and order.payment_status == "SUCCESS"
        ):
            wallet = Wallet.objects.select_for_update().get(user=request.user)

            wallet.balance += order.total_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=order.total_amount,
                txn_type="CREDIT"
            )

            order.payment_status = "REFUNDED"

        order.save()

        messages.success(
            request,
            "Order cancelled successfully. "
            + ("Amount refunded to wallet." if order.payment_method == "ONLINE" else "")
        )

        return redirect("order_detail", order_id=order.order_id)

    # GET → show cancel confirmation page
    return render(request, "cancel_order.html", {
        "order": order,
        "reasons": Order.CANCEL_REASONS
    })
    
@login_required
def buy_now(request, variant_id):
    variant = get_object_or_404(SizeVariant, id=variant_id)

    quantity = int(request.POST.get("quantity", 1))
    quantity = max(1, quantity)

    subtotal = variant.price * quantity
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")
    total = subtotal + delivery

    order = Order.objects.create(
        user=request.user,
        address=Address.objects.filter(user=request.user, is_default=True).first(),
        order_items_total=subtotal,
        delivery_charge=delivery,
        total_amount=total,
        delivery_date=date.today() + timedelta(days=3),
        status="PENDING"
    )

    OrderItem.objects.create(
        order=order,
        variant=variant,
        quantity=quantity,
        price=variant.price
    )

    return redirect("pay_order", order_id=order.order_id)

@login_required
def confirm_payment(request, order_id):
    if request.method != "POST":
        return redirect("pay_order", order_id=order_id)

    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    payment_method = request.POST.get("payment_method")

    if payment_method != "COD":
        messages.error(request, "Please select a payment method.")
        return redirect("pay_order", order_id=order_id)

    order.payment_method = "COD"
    order.payment_status = "PENDING"
    order.save()

    return redirect("order_success", order_id=order.order_id)

def mark_order_delivered(order):
    order.status = "DELIVERED"
    order.payment_status = "SUCCESS"
    order.paid_at = timezone.now()  
    order.save()
    
    method = (order.payment_method or "COD").upper(),

    Payment.objects.get_or_create(
        order=order,
        defaults={
            "txn_id": f"COD-{uuid.uuid4()}",
            "method": method,
            "status": "SUCCESS",
            "amount": order.total_amount,
        }
    )

@login_required
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "failed"}, status=400)

    data = json.loads(request.body)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        })

        order = Order.objects.get(order_id=data["order_id"], user=request.user)
        
        order.payment_method = "ONLINE"
        order.payment_status = "SUCCESS"
        order.status = "CONFIRMED"
        order.paid_at = timezone.now()
        order.save()

        Payment.objects.create(
            order=order,
            txn_id=data["razorpay_payment_id"],
            method="ONLINE",
            status="SUCCESS",
            amount=order.total_amount
        )

        return JsonResponse({"status": "success"})

    except Exception as e:
        return JsonResponse({"status": "failed"})