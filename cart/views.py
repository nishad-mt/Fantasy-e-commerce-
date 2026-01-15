from django.shortcuts import render,redirect
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem
from wishlist.models import WishlistModel, WishlistItem
from products.models import SizeVariant
from django.contrib import messages
from decimal import Decimal

@login_required
def toggle_cart(request, variant_id):
    if request.method == "POST":
        variant = get_object_or_404(SizeVariant, id=variant_id, is_available=True)

        quantity = int(request.POST.get("quantity", 1))

        cart, _ = Cart.objects.get_or_create(user=request.user)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={"quantity": quantity}
        )

        if not created:
            item.quantity += quantity
            item.save()

        # ✅ success message
        messages.success(request, "Added to cart")

    return redirect(request.META.get("HTTP_REFERER", "products"))

@login_required
def cart(request):
    cart = Cart.objects.get(user=request.user)
    items = (CartItem.objects.filter(cart__user=request.user).select_related('variant', 'variant__product')).order_by('-added_at')
    
    subtotal = 0
    total_items = 0
    
    for item in items:
        item.total_price = item.variant.price*item.quantity
        subtotal += item.total_price
        total_items += item.quantity
        
    item_count = items.count()
    
    delivery_charge = 0 if subtotal > 500 else 40
    discount = 0
    total = subtotal + delivery_charge - discount
    
    context = {
        "items": items,
        "subtotal": subtotal,
        "total_items": total_items,
        "delivery_charge": delivery_charge,
        "discount": discount,
        "total": total,
        "item_count":item_count
    }
    return render(request, 'cartlist.html', context)

@login_required
def remove_cart(request,variant_id):
    if request.method == "POST":
        CartItem.objects.filter(cart__user=request.user,variant_id=variant_id).delete()
        return redirect('cart:cart')
    

@login_required
def move_to_wishlist(request, variant_id):
    cart = get_object_or_404(Cart, user=request.user)

    cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)

    product = cart_item.variant.product

    wishlist, _ = WishlistModel.objects.get_or_create(user=request.user)

    WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        product=product
    )
    cart_item.delete()

    return redirect("cart:cart")   
