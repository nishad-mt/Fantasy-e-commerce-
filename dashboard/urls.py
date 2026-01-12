from django.urls import path
from . import views

urlpatterns = [
    path("",views.admin_login,name="admin_log"),
    path("dashboard/",views.dashboard,name="dashboard"),
    path("control_user/",views.user,name="user"),
    path('block-user/<uuid:user_id>/', views.block, name='block_user'),
    path('unblock-user/<uuid:user_id>/', views.unblock, name='unblock_user'),
    path("manage_products/",views.adm_products,name="admin_products"),
    path("manage_offers/",views.offers_management,name="offers"),
    path("manage_categories/",views.categories,name="categories"),
    path("orders/",views.orders,name="orders"),
    path("review_payments/",views.Payments,name="payments"),
    path("delivery/",views.deliveries,name="delivery"),
    path("reviews/",views.reviews,name="reviews"),
    path("admin_logout/",views.admin_logout,name="admin_logout"),
]
