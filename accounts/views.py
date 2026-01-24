from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.utils import timezone   
from datetime import timedelta      
import random
from django.contrib.auth import authenticate, login as auth_login, logout 
from django.contrib.auth.decorators import login_required
from addresses.models import Address
from .forms import CustomUserForm, UserProfileForm
from .models import CustomUser, UserProfile
from django.views.decorators.cache import never_cache
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.urls import reverse


User = get_user_model()

@never_cache
def signup(request):
    if request.user.is_authenticated or request.session.get("is_email_vfd"):
        return redirect("home")
    
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            # Save form data in session temporarily
            request.session['signup_data'] = form.cleaned_data

            # Generate OTP
            otp = random.randint(1000, 9999)
            request.session['otp'] = otp
            request.session['email'] = form.cleaned_data['email']
            request.session['otp_last_sent'] = timezone.now().isoformat()#converts datetime to a standard string format that everyone understands.

            # Send OTP
            send_otp(form.cleaned_data['email'], otp)

            messages.success(request, "OTP sent to your email.")
            return redirect('verify_otp')
    else:
        form = CustomUserForm()

    return render(request, 'signup.html', {'form': form})

#(who, what)
def send_otp(email, otp):
    subject = "Your Verification OTP for Fantasy Food Products"
    message = f"Your OTP is: {otp}\n Don't share the otp to anyone"
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
    except BadHeaderError:
        print("Invalid header found.")
    except Exception as e:
        print(f"Error sending email: {e}")

@never_cache
def verify_otp(request):
    if request.session.get("is_email_vfd"):
        return redirect("home")
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        saved_otp = request.session.get('otp')
        email = request.session.get('email')
        
        if not saved_otp or not email:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect('signup')

        if str(entered_otp) == str(saved_otp):
            request.session["is_email_vfd"] = True
            data = request.session.get('signup_data')
            if not data:
                messages.error(request, "Session expired. Please sign up again.")
                return redirect('signup')

            # Create user ,store to db if otp is correct
            user = CustomUser.objects.create_user(
                email=data['email'],
                username=data['username'],
                password=data['password1'],
            )
            user.is_active = True
            user.save()

            # Auto-create profile
            UserProfile.objects.get_or_create(user=user)#first user:The newly created CustomUser object
                                                        #second user:  The exact same data object passed to UserProfile
            # Auto-login
            auth_login(
                request,
                user,
                backend='django.contrib.auth.backends.ModelBackend'
            )

            # Clear session
            for key in ['signup_data', 'otp', 'email', 'otp_last_sent']:
                if key in request.session:
                    del request.session[key]

            messages.success(request, "Account verified successfully!")
            return redirect('home')
        else:
            messages.error(request, "Invalid OTP.")
            return redirect('verify_otp') 

    return render(request, 'otp.html')

def resend_otp(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('signup')

    last_sent = request.session.get("otp_last_sent")
    if last_sent:
        last_sent_time = timezone.datetime.fromisoformat(last_sent)
        if timezone.now() < last_sent_time + timedelta(seconds=60):
            remaining = (last_sent_time + timedelta(seconds=60)) - timezone.now()
            messages.error(request, f"Please wait {int(remaining.total_seconds())} seconds before resending OTP.")
            return redirect("verify_otp")

    otp = random.randint(1000, 9999)
    request.session["otp"] = otp
    request.session["otp_last_sent"] = timezone.now().isoformat()
    send_otp(email, otp)
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("verify_otp")
@never_cache
def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            auth_login(request, user)

            if user.is_staff or user.is_superuser:
                return redirect('/admin/')

            return redirect('home')

        messages.error(request, "Invalid email or password.")

    return render(request, 'login.html')
 
@never_cache
def user_logout(request):
    logout(request)
    return redirect('home')

@never_cache
@login_required
def profile(request):
    if request.user.is_staff:
        return redirect('/admin_user/')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    return render(request, 'user_profile.html', {
        'profile': profile,
        'addresses': addresses,
        'default_address': default_address
    })

@login_required
@never_cache
def edit_profile(request):
    #_ is used to ignore the second value returned by get_or_create() when you don’t need it.
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully")
            return redirect("profile")
    else:
        profile_form = UserProfileForm(instance=profile)

    return render(request, "edit_profile.html", {
        "profile_form": profile_form,
    })

@never_cache
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)

            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_path = reverse(
                'new_password',
                kwargs={'uidb64': uidb64, 'token': token}
            )

            reset_link = f"{request.scheme}://{request.get_host()}{reset_path}"

            send_mail(
                subject="Reset your password",
                message=f"Click the link to reset your password:\n\n{reset_link}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False
            )

            messages.success(request, "Password reset link sent to your email.")

        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")

        return redirect('forgot_password')

    return render(request, 'forgot.html')

@never_cache
def new_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Password reset link is invalid or expired")
        return redirect('login')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'new_pass.html')

        user.set_password(new_password)
        user.save(update_fields=['password'])

        auth_login(
            request,
            user,
            backend='django.contrib.auth.backends.ModelBackend'
        )

        messages.success(request, "Password updated successfully")

        if user.is_staff or user.is_superuser:
            return redirect('admin_log') 
        return redirect('login')

    return render(request, 'new_pass.html')
