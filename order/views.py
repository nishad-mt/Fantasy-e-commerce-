from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from cart.models import Cart,CartItem
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
    if not Address.objects.filter(user=request.user).exists():
        messages.warning(
            request,
            "Please add a delivery address before placing an order."
        )
        return redirect("create_address")
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
        status="PENDING",
        source="CART"

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
    if not addresses.exists():
        messages.warning(
            request,
            "Please add a delivery address to continue."
        )
        return redirect("create_address")

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
        return JsonResponse({"error": "Invalid request"}, status=400)

    order_id = request.POST.get("order_id")

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status="PENDING"
    )

    items = order.items.select_related("variant")

    if not items.exists():
        return JsonResponse({
            "status": "error",
            "message": "Order has no items."
        }, status=400)

    if not order.address:
        return JsonResponse({
            "status": "no_address",
            "message": "Please select a delivery address."
        })

    # ---------- Recalculate totals (SECURITY) ----------
    subtotal = sum(item.variant.price * item.quantity for item in items)
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")
    total = subtotal + delivery

    order.order_items_total = subtotal
    order.delivery_charge = delivery
    order.total_amount = total
    order.delivery_date = date.today() + timedelta(days=3)

    payment_method = request.POST.get("payment_method")

    # =================================================
    # CASH ON DELIVERY
    # =================================================
    if payment_method == "COD":
        order.payment_method = "COD"
        order.payment_status = "PENDING"
        order.save()

        return JsonResponse({
            "status": "cod_confirm",
            "order_id": order.order_id
        })

    # =================================================
    # WALLET PAYMENT
    # =================================================
    elif payment_method == "WALLET":
        wallet = Wallet.objects.select_for_update().get(user=request.user)

        if wallet.balance < total:
            return JsonResponse({
                "status": "wallet_insufficient",
                "message": "Insufficient wallet balance."
            })

        wallet.balance -= total
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            order=order,
            amount=total,
            txn_type="DEBIT"
        )

        order.payment_method = "WALLET"
        order.payment_status = "SUCCESS"
        order.paid_at = timezone.now()
        order.save()

        Payment.objects.create(
            user=request.user,
            order=order,
            razorpay_order_id=f"WALLET-{uuid.uuid4()}",
            razorpay_payment_id=f"WALLET-{uuid.uuid4()}",
            gateway_method="WALLET",
            amount=total,
            status="SUCCESS"
        )

        # 🧹 clear cart ONLY if order came from cart
        if order.source == "CART":
            CartItem.objects.filter(cart__user=request.user).delete()

        return JsonResponse({
            "status": "wallet_success",
            "order_id": order.order_id
        })

    # =================================================
    # ONLINE PAYMENT (RAZORPAY)
    # =================================================
    elif payment_method == "ONLINE":
        order.payment_method = "ONLINE"
        order.payment_status = "PENDING"
        order.save()

        return JsonResponse({
            "status": "online",
            "order_id": order.order_id
        })

    return JsonResponse({
        "status": "invalid_payment",
        "message": "Invalid payment method."
    }, status=400)

@login_required
@transaction.atomic
def confirm_cod(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    data = json.loads(request.body)
    order_id = data.get("order_id")

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status="PENDING"
    )

    # Finalize COD order
    order.payment_method = "COD"
    order.payment_status = "PENDING"
    order.save()

    # Clear cart
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        cart.items.all().delete()

    return JsonResponse({
        "status": "success",
        "order_id": order.order_id
    })


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
    if order.status == "CANCELLED":
        messages.error(request, "Order already cancelled.")
        return redirect("order_detail", order_id=order.order_id)

    if order.status not in ["PENDING", "CONFIRMED"]:
        messages.error(request, "This order cannot be cancelled.")
        return redirect("order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("cancel_reason")

        if not reason:
            messages.error(request, "Please select a cancellation reason.")
            return redirect("order_detail", order_id=order.order_id)

        
        # CANCEL ORDER
        order.status = "CANCELLED"
        order.cancel_reason = reason
        order.cancelled_at = timezone.now()

        # WALLET REFUND (ONLINE)
        if order.payment_method in ["ONLINE", "WALLET"] and order.payment_status == "SUCCESS":

            wallet, created = Wallet.objects.select_for_update().get_or_create(
                user=request.user
            )

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

    return redirect("order_detail", order_id=order.order_id)

    
@login_required
def buy_now(request, variant_id):

    if not Address.objects.filter(user=request.user).exists():
        messages.warning(
            request,
            "Please add a delivery address before placing an order."
        )
        return redirect("create_address")
    
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
        status="PENDING",
        source="BUY_NOW"
    )

    OrderItem.objects.create(
        order=order,
        variant=variant,
        quantity=quantity,
        price=variant.price
    )

    return redirect("pay_order", order_id=order.order_id)


