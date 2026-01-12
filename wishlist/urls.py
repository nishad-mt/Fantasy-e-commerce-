from django.urls import path
from . import views
app_name = 'wishlist'   

urlpatterns = [
    path('toggle/<uuid:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('', views.wishlist, name='wishlist'),
]
