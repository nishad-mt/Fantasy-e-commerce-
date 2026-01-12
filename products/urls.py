from django.urls import path
from . import views

urlpatterns = [
    path("products/",views.products,name="products"),
    path("products_description/<slug:slug>",views.user_product_details,name="user_product"),
    path('products/category/<slug:slug>/', views.products, name='products_by_category'),
    path("add_products/",views.add_products,name="add_products"),
    path("del_products/<uuid:product_id>",views.del_product,name="del_products"),
    path("add_category/",views.add_category,name="add_category"),
    path("edit_products/<slug:slug>",views.edit_product,name="edit_product"),
    path("product/<slug:slug>/images/", views.product_detail, name="product_image"),
    path("edit_category/<uuid:category_id>",views.edit_category,name="edit_category"),
    path("delete_category/<uuid:category_id>",views.del_category,name="del_category"),
    path("product_review/",views.product_review,name="product_review"),
]
