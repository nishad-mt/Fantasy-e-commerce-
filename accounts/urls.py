from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),

    path("verify_otp/",views.verify_otp,name="verify_otp"),
    path("resend_otp/",views.resend_otp,name="resend_otp"),
    path("profile/",views.profile,name="profile"),
    path("edit-profile/",views.edit_profile,name="edit_profile"),
    path("logout/",views.user_logout,name="logout"),
    path("forgot-password/",views.forgot_password,name="forgot_password"),
    path("new-password/<uidb64>/<token>/",views.new_password,name="new_password"),
    
]
