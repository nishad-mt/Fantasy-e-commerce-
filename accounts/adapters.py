import uuid
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        extra_data = sociallogin.account.extra_data
        name = extra_data.get("name")

        if name:
            user.username = name
        else:
            user.username = f"user_{uuid.uuid4().hex[:8]}"
            
        # Mark provider
        user.auth_provider = "google"
        user.is_email_vfd = True

        # Google users should not use passwords
        user.set_unusable_password()

        user.save()
        return user
