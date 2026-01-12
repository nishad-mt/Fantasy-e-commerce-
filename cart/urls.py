from django.urls import path
from . import views

app_name = 'cart'   

urlpatterns = [
    path('toggle/<int:variant_id>/', views.toggle_cart, name='toggle_cart'),
    path('', views.cart, name='cart'),
    path('remove/<int:variant_id>', views.remove_cart, name='remove_cart'),
]
