from django.urls import path
from . import views

urlpatterns = [
    path("",views.order,name="order"),
    path("checkout-order/",views.checkout,name="checkout"),
    path("order-detail/",views.order_detail,name="order_detail"),
  
]