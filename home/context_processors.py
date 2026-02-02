from .models import SiteContact

def contact_details_processor(request):
    return {
        "contact_details": SiteContact.objects.first()
    }
