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

def order(request):
    orders = Order.objects.filter(user=request.user).prefetch_related(
        "items__variant__product"
    ).order_by("-created_at")

    return render(request,"order.html",{
        'orders':orders,
        }
                  )

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
    order = get_object_or_404(Order,
                              order_id=order_id,
                              user=request.user
                              )
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
def cancel_order_request(request, order_id):
    order = get_object_or_404(Order,order_id=order_id,user=request.user)

    if order.status not in ["PENDING", "CONFIRMED"]:
        messages.error(
            request,
            "This order can no longer be cancelled."
        )
        return redirect("order_detail", order_id=order.order_id)

    order.status = "CANCELLED"

    if order.payment_method != "COD":
        order.payment_status = "FAILED"

    order.save()

    messages.success(
        request,
        "Your order has been cancelled successfully."
    )

    return redirect("order_detail", order_id=order.order_id)

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

    if payment_method not in ["COD", "UPI", "CARD"]:
        messages.error(request, "Please select a payment method.")
        return redirect("pay_order", order_id=order_id)

    order.payment_method = payment_method
    order.payment_status = "PENDING"
    order.save()

    return redirect("order_success", order_id=order.order_id)

def mark_order_delivered(order):
    order.status = "DELIVERED"
    order.payment_status = "SUCCESS"
    order.save()

    Payment.objects.get_or_create(
        order=order,
        method=order.payment_method,
        defaults={
            "txn_id": f"{order.payment_method}-{uuid.uuid4()}",
            "status": "SUCCESS",
            "amount": order.total_amount,
        }
    )