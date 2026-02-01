from django.urls import path
from . import views

urlpatterns = [
    path(
        "create-razorpay-order/",
        views.create_razorpay_order,
        name="create_razorpay_order"
    ),
    path(
        "verify/",
        views.verify_payment,
        name="verify_payment"
    ),
    path(
        "razorpay-webhook/",
        views.razorpay_webhook,
        name="razorpay_webhook"
    ),
]
