from django.shortcuts import render,redirect
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem
from products.models import SizeVariant
from django.contrib import messages

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
    items = (CartItem.objects.filter(cart__user=request.user).select_related('variant', 'variant__product')).order_by('-added_at')

    item_count = items.count()

    context = {
        'items': items,
        'item_count': item_count
    }
    return render(request, 'cartlist.html', context)

@login_required
def remove_cart(request,variant_id):
    if request.method == "POST":
        CartItem.objects.filter(cart__user=request.user,variant_id=variant_id).delete()
        return redirect('cart:cart')