from django.urls import path
from . import views

urlpatterns = [
    path("wallet/", views.wallet, name="wallet"),
    path("admin/wallets/<uuid:user_id>/", views.admin_user_wallet_detail, name="admin_user_wallet_detail"),

]
