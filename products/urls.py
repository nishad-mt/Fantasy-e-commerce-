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
    
    path("review/write/<slug:slug>/", views.write_review, name="write_review"),
    path("review/edit/<uuid:review_id>/", views.edit_review, name="edit_review"),
    path("review/delete/<uuid:review_id>/", views.delete_review, name="delete_review"),
    path("admin/reviews/update/<uuid:review_id>/", views.update_review_status, name="update_review_status"),


]
