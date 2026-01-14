from django.urls import path
from . import views

urlpatterns = [
    path("",views.order,name="order"),
    path("from-cart/", views.create_from_cart, name="create_from_cart"),
    path("pay/<uuid:order_id>/", views.pay_order, name="pay_order"),
    path("checkout-order/",views.checkout,name="checkout"),
    path("order-detail/",views.order_detail,name="order_detail"),
  
]