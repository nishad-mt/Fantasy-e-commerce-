from django.contrib.auth import logout, login ,get_user_model
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LoginForm
from django.contrib.auth.decorators import login_required
from products.models import Categories,Product,ProductReview
from order.models import Order
from payment.models import Payment
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from accounts.decarators import admin_required
from django.db.models import Avg, Count, Sum
from datetime import date, timedelta
from home.models import SiteContact,ContactMessage
from django.utils.timezone import now
import uuid
import json
from django.utils import timezone


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
    
    today = timezone.now().date()
    todays_order_count = Order.objects.filter(
        created_at__date=today
    ).count()
    
    rec_users = User.objects.order_by('-joined_at')[:5]
    
    products = Product.objects.annotate(
    wishlist_count=Count("wishlistitem", distinct=True),
    cart_count=Count("variants__cartitem", distinct=True),
    ordered_count=Count(
        "variants__orderitem",
        filter=Q(variants__orderitem__order__status__in=["CONFIRMED", "PACKED", "DELIVERED"]),
        distinct=True
    )
    ).order_by("-ordered_count", "-cart_count", "-wishlist_count")
    
    todays_revenue = Order.objects.filter(
    paid_at__date=today,
    payment_status="SUCCESS"
).aggregate(
    total=Sum("total_amount")
)["total"] or 0


    sitedetails = SiteContact.objects.first()
    pending_orders = Order.objects.filter(
    status__in=["PENDING", "CONFIRMED"]
).order_by("-created_at")

    context = {
        'total_users': total_users,
        'total_products':total_products, 
        'rec_users':rec_users,
        'products':products,
        'sitedetails':sitedetails,
        'todays_order_count':todays_order_count,
        'todays_revenue':todays_revenue,
        'pending_orders':pending_orders
    }

    return render(request, "dashboard.html", context)

@never_cache
@login_required
def user(request):
    users = User.objects.select_related('profile').all()
    
    ordered_user_count = User.objects.filter(order__isnull=False).distinct().count()

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
        'ordered_user_count':ordered_user_count
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


@staff_member_required
def admin_order_list(request):
    orders = Order.objects.all().order_by("-created_at")

    search = request.GET.get("search")
    if search:
        orders = orders.filter(
            Q(order_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(address__phone__icontains=search)
        )

    status = request.GET.get("status")
    if status and status != "all":
        orders = orders.filter(status=status.upper())

    payment = request.GET.get("payment")
    if payment == "COD":
        orders = orders.filter(payment_method="COD")
    elif payment == "Online":
        orders = orders.exclude(payment_method="COD")

    date_filter = request.GET.get("date")
    today = date.today()

    if date_filter == "today":
        orders = orders.filter(
            Q(paid_at__date=today) |
            Q(paid_at__isnull=True, created_at__date=today)
        )
    elif date_filter == "week":
        orders = orders.filter(
            Q(paid_at__date__gte=today - timedelta(days=7)) |
            Q(paid_at__isnull=True, created_at__date__gte=today - timedelta(days=7))
        )
    elif date_filter == "month":
        orders = orders.filter(
            Q(paid_at__month=today.month) |
            Q(paid_at__isnull=True, created_at__month=today.month)
        )

    STATUS_FLOW = {
        "PENDING": ["CONFIRMED", "CANCELLED"],
        "CONFIRMED": ["PACKED"],
        "PACKED": ["DELIVERED"],
    }

    for order in orders:
        order.next_actions = STATUS_FLOW.get(order.status, [])

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        new_status = request.POST.get("status")

        order = get_object_or_404(Order, order_id=order_id)

        if order.payment_method != "COD" and order.payment_status != "SUCCESS":
            messages.error(request, "Payment not verified.")
            return redirect("orders")

        if new_status not in STATUS_FLOW.get(order.status, []):
            messages.error(request, "Invalid status update.")
            return redirect("orders")

        order.status = new_status

        if new_status == "DELIVERED" and order.payment_method == "COD":
            order.payment_status = "SUCCESS"
            order.paid_at = timezone.now()

            Payment.objects.get_or_create(
                order=order,
                method="COD",
                defaults={
                    "txn_id": f"COD-{uuid.uuid4()}",
                    "status": "SUCCESS",
                    "amount": order.total_amount,
                }
            )

        order.save()
        messages.success(request, "Order status updated.")
        return redirect("orders")

    return render(request, "admin_orders.html", {
        "orders": orders,
        "filters": {
            "search": search or "",
            "status": status or "all",
            "payment": payment or "all",
            "date": date_filter or "all",
        }
    })


@admin_required
@login_required
def admin_payments_dashboard(request):
    today = now().date()
    start_month = today.replace(day=1)

    total_revenue = (
        Payment.objects.filter(status="SUCCESS")
        .aggregate(total=Sum("amount"))["total"] or 0
    )

    today_collection = (
        Payment.objects.filter(
            status="SUCCESS",
            created_at__date=today
        ).aggregate(total=Sum("amount"))["total"] or 0
    )

    successful_txns = Payment.objects.filter(
        status="SUCCESS",
        created_at__date__gte=start_month
    ).count()

    transactions_qs = (
        Payment.objects
        .select_related("order", "order__user")
        .order_by("-created_at")
    )

    txn_list = []
    for txn in transactions_qs:
        user = txn.order.user

        customer_name = (
            f"{user.username}"
            or user.username
            or user.email
        )

        txn_list.append({
            "id": txn.txn_id,
            "orderId": str(txn.order.order_id),
            "customer": customer_name,
            "method": (txn.method or "UNKNOWN").upper(),   
            "amount": float(txn.amount),
            "status": txn.status.title(),
            "date": txn.created_at.strftime("%Y-%m-%d %I:%M %p"),
        })

    method_chart = dict(
        Payment.objects.filter(status="SUCCESS")
        .values_list("method")
        .annotate(count=Count("id"))
    )

    method_chart = {
        (k or "UNKNOWN").upper(): v
        for k, v in method_chart.items()
    }

    revenue_labels = []
    revenue_data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        amount = (
            Payment.objects.filter(
                status="SUCCESS",
                created_at__date=day
            ).aggregate(total=Sum("amount"))["total"] or 0
        )

        revenue_labels.append(day.strftime("%a"))
        revenue_data.append(float(amount))

    context = {
        "total_revenue": float(total_revenue),
        "today_collection": float(today_collection),
        "successful_txns": successful_txns,

        "transactions": json.dumps(txn_list),
        "revenue_labels": json.dumps(revenue_labels),
        "revenue_data": json.dumps(revenue_data),
        "method_chart": json.dumps(method_chart),
    }

    return render(request, "payments.html", context)

@admin_required
def admin_contact(request):
    contact_info, _ = SiteContact.objects.get_or_create(
        id=1,
        defaults={
            "address": "",
            "contact_number": "",
            "email": "",
            "is_active": True,
        }
    )

    messages = ContactMessage.objects.all().order_by("-created_at")
    q = request.GET.get("q")
    status = request.GET.get("status")

    if q:
        messages = messages.filter(
            Q(name__icontains=q) |
            Q(number__icontains=q) |
            Q(message__icontains=q)
        )

    if status:
        messages = messages.filter(status=status)

    context = {
        "contact": contact_info,
        "messages": messages,
        "total_messages": messages.count(),
        "pending_messages": messages.filter(status="pending").count(),
        "replied_messages": messages.filter(status="replied").count(),
    }

    return render(request, "admin_contact.html", context)

@never_cache
@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_log')