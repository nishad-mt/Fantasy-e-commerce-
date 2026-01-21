from django.urls import path
from . import views

urlpatterns = [
    path("",views.home,name="home"),
    path("about_us/",views.about,name="aboutus"),
    path("contact_us/",views.contact,name="contact"),
    path("admin_contact/update/",views.update_site_contact,name="update_site_contact"),
    path("contact_message/update/",views.contact_message,name="contact_message"),
    
]
