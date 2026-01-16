from django.contrib.auth import logout, login ,get_user_model
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LoginForm
from django.contrib.auth.decorators import login_required
from products.models import Categories,Product,SizeVariant,ProductReview
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.db.models import Prefetch
from accounts.decarators import admin_required
from django.db.models import Avg, Count



User = get_user_model()

@never_cache
def admin_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm()

    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            logged_user = form.cleaned_data['user']

            if User.is_staff or User.is_superuser:
                login(request, logged_user)
                return redirect('dashboard')
            else:
                messages.error(request, "You are not authorized as admin")

    return render(request, "admin_login.html", {'form': form})

@never_cache
@login_required
def dashboard(request):
    total_users = User.objects.count()
    total_products = Product.objects.count()
    rec_users = User.objects.order_by('-joined_at')[:5]
    products = Product.objects.annotate(
    wishlist_count=Count("wishlistitem", distinct=True),
    cart_count=Count("variants__cartitem", distinct=True)
).order_by("-wishlist_count", "-cart_count")
    
    context = {
        'total_users': total_users,
        'total_products':total_products, 
        'rec_users':rec_users,
        'products':products
    }

    return render(request, "dashboard.html", context)

@never_cache
@login_required
def user(request):
    users = User.objects.select_related('profile').all()

    total_users = User.objects.count()
    active_users_count = User.objects.filter(is_active = True).count()
    blocked_users_count = User.objects.filter(is_active = False).count()
    query = request.GET.get('q','')
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    
    role = request.GET.get('role')
    status = request.GET.get('status')
    joined = request.GET.get('joined')
    
    if role == 'admin':
        users = users.filter(is_staff=True)
    elif role == 'customer':
        users = users.filter(is_staff=False)

    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'blocked':
        users = users.filter(is_active=False)

    if joined:
        users = users.filter(joined_at=joined)

    context = {
        'users': users,
        'total_users': total_users,
        'active_users_count': active_users_count,
        'blocked_users_count': blocked_users_count,
        'query':query,
    }

    return render(request, "user.html", context)

@never_cache
@login_required
def block(request, user_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized access")
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "You cannot block yourself")
        return redirect('dashboard')

    if user.is_superuser:
        messages.error(request, "You cannot block an admin user")
        return redirect('dashboard')

    user.is_active = False
    user.save(update_fields=['is_active'])  

    messages.success(request, f"{user.username or user.email} has been blocked")
    return redirect('user')
@never_cache
@login_required
def unblock(request,user_id):
    if not request.user.is_staff:
        messages.error(request,'Unauthorized access')
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    if user.is_active:
        messages.warning(request, "User is already active")
        return redirect('dashboard')
    
    user.is_active = True
    user.save(update_fields=['is_active'])

    messages.success(request, f"{user.username} has been unblocked")
    return redirect('user')
 
@never_cache
@login_required
def adm_products(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        
        product = get_object_or_404(Product, product_id=product_id)
        
        if action == 'delete' and request.user.has_perm('products.delete_product'):
            product.delete()
            messages.success(request, f'{product.name} deleted successfully!')
        elif action == 'hide':
            product.is_active = False
            product.save()
            messages.success(request, f'{product.name} hidden!')
        elif action == 'show':
            product.is_active = True
            product.save()
            messages.success(request, f'{product.name} shown!')
            
    ctgry = Categories.objects.all()
    items = Product.objects.all().prefetch_related('variants')
    for p in items:
        cheapest = p.variants.filter(is_available=True).order_by("price").first()
        if cheapest:
            p.min_price = cheapest.price
            p.min_size = cheapest.size_name
        else:
            p.min_price = None
            p.min_size = None
    recently_added = Product.objects.all().order_by('-created_at')[:3]
    query = request.GET.get('q', '').strip()
    if query:
        items = items.filter(
            Q(name__icontains=query) | 
            Q(sku__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    total_product = Product.objects.count()
    active_product_count = Product.objects.filter(is_active = True).count()
    out_of_stock_count = Product.objects.filter(is_active = False).count()
    
    price = request.GET.get('price')
    if price == 'low':
        items = items.filter(base_price__lt=50)
    elif price == 'high':
        items = items.order_by('-base_price')
    elif price == 'med':
        items = items.order_by('base_price')
        
    cat_slug = request.GET.get('categories')
    if cat_slug:
        items = items.filter(category__slug=cat_slug)
    
    # Stock filter
    stock = request.GET.get('stock')
    if stock == 'in':
        items = items.filter(sizes__is_available=True).distinct()
    elif stock == 'out':
        # Fallback to is_active if no SizeVariant
        items = items.filter(is_active=False)
    
        
    context ={
        'items':items,
        'category':ctgry,
        'total_product':total_product,
        'active_product_count':active_product_count,
        'outof_stock_count':out_of_stock_count,
        'query':query,
        'recently_added':recently_added,
    }
    
    return render(request,"adm_pdct.html",context)

@never_cache
@login_required
def offers_management(request):
    return render(request,"offers_adm.html")

@never_cache
@login_required
def categories(request):
    ctgry = Categories.objects.prefetch_related(
    Prefetch(
        "products",
        queryset=Product.objects.filter(is_active=True),
        to_attr="active_products"
    ),
    Prefetch(
        "products",
        queryset=Product.objects.filter(is_active=False),
        to_attr="inactive_products"
    )
)
    categories_count = ctgry.count()
    product_count = Product.objects.all().count()
    active_categories = Categories.objects.filter(is_active = True).count()
    hidden_categories = Categories.objects.filter(is_active = False).count()
    
    status = request.GET.get('status')
    
    if status == 'active':
        ctgry = ctgry.filter(is_active=True)
    elif status == 'hidden':
        ctgry = ctgry.filter(is_active=False)
    
    context = {
        'ctg_count':categories_count,
        'categories':ctgry,
        'active_categories':active_categories,
        'hidden_categories':hidden_categories,
        'product_count':product_count,
    }
    return render(request,"adm_categories.html",context)

@login_required
@admin_required
def admin_reviews(request):
    reviews = ProductReview.objects.select_related("product", "user")

    # Filters
    status = request.GET.get("status")
    rating = request.GET.get("rating")
    search = request.GET.get("search")

    if status == "approved":
        reviews = reviews.filter(is_approved=True)
    elif status == "pending":
        reviews = reviews.filter(is_approved=False)

    if rating:
        if rating == "5":
            reviews = reviews.filter(rating=5)
        elif rating == "4":
            reviews = reviews.filter(rating__gte=4)
        elif rating == "3":
            reviews = reviews.filter(rating__gte=3)
        elif rating == "low":
            reviews = reviews.filter(rating__lte=2)

    if search:
        reviews = reviews.filter(
            Q(product__name__icontains=search) |
            Q(user__username__icontains=search)
        )

    # Stats
    total_reviews = ProductReview.objects.count()
    avg_rating = ProductReview.objects.aggregate(avg=Avg("rating"))["avg"] or 0
    pending_count = ProductReview.objects.filter(is_approved=False).count()
    verified_count = ProductReview.objects.filter(is_verified_purchase=True).count()

    context = { 
        "reviews": reviews,
        "total_reviews": total_reviews,
        "avg_rating": round(avg_rating, 1),
        "pending_count": pending_count,
        "verified_count": verified_count,
    }
    return render(request, "admin_reviews.html", context)

@never_cache
@login_required
def orders(request):
    return render(request,"admin_orders.html")

@never_cache
@login_required
def Payments(request):
    return render(request,"payments.html")

@never_cache
@login_required
def deliveries(request):
    return render(request,"delivery.html")


@never_cache
def admin_contact(request):
    return render(request,"admin_contact.html")

@never_cache
@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_log')