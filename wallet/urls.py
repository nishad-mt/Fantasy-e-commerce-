from django.urls import path
from . import views

urlpatterns = [
    path("", views.wallet_detail, name="wallet"),
    path("transactions/", views.wallet_transactions, name="wallet_transactions"),
]
