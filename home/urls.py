from django.urls import path
from . import views

urlpatterns = [
    path("",views.home,name="home"),
    path("about_us/",views.about,name="aboutus"),
    path("contact_us/",views.contact,name="contact"),
]
