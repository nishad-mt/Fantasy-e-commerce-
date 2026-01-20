from django.urls import path
from . import views

urlpatterns = [
    path("",views.order,name="order"),
    path("from-cart/", views.create_from_cart, name="create_from_cart"),
    path("admin_order_detail/<uuid:order_id>/", views.admin_order_detail, name="admin_order_detail"),
    path("choose_address/", views.select_address, name="select_address"),
    path("place/", views.place_order, name="place_order"),
    path("pay/<uuid:order_id>/", views.pay_order, name="pay_order"),
    path("checkout-order/",views.checkout,name="checkout"),
    path("order-detail/<uuid:order_id>",views.order_detail,name="order_detail"),
    path("success/<str:order_id>/", views.order_success, name="order_success"),
  
]