from django.urls import path
from . import views

urlpatterns = [
    path("admin/promotions/", views.promotion_list, name="promotion_list"),
    path("admin/promotions/create/", views.create_promotion, name="create_promotion"),
    path("admin/promotions/<int:promotion_id>/edit/",views.edit_promotion,name="edit_promotion"),
    path("admin/promotions/<int:promotion_id>/delete/",views.delete_promotion,name="delete_promotion"),
    path("apply_coupon",views.apply_coupon,name="apply_coupon")

]
