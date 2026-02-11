from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.utils import timezone   
from datetime import timedelta      
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login as auth_login, logout 
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
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
from django.utils.dateparse import parse_datetime
from wallet.models import Wallet
import secrets
from django.db import transaction, IntegrityError
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now


User = get_user_model()

@never_cache
def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = CustomUserForm(request.POST)
        if form.is_valid():
            
            email = form.cleaned_data["email"]

            # OTP cooldown
            last_sent = request.session.get("otp_last_sent")
            if last_sent:
                last_sent_time = parse_datetime(last_sent)
                if timezone.now() < last_sent_time + timedelta(seconds=60):
                    messages.error(request, "Please wait before requesting another OTP.")
                    return redirect("verify_otp")

            # Clear old OTP safely
            request.session.pop("otp", None)
            request.session.pop("email", None)
            request.session.pop("signup_data", None)

            request.session["signup_data"] = {
                "email": email,
                "username": form.cleaned_data["username"],
                "password": form.cleaned_data["password1"],
            }

            import secrets
            otp = secrets.randbelow(9000) + 1000

            request.session["otp"] = otp
            request.session["email"] = email
            request.session["otp_last_sent"] = timezone.now().isoformat()

            try:
                send_otp(email, otp)
            except Exception:
                messages.error(request, "Failed to send OTP. Try again.")
                return redirect("account_signup")

            messages.success(request, "OTP sent to your email.")
            return redirect("verify_otp")
    else:
        form = CustomUserForm()

    return render(request, "signup.html", {"form": form})

#(who, what)
def send_otp(email, otp):
    if not email or not otp:
        raise ValueError("Email and OTP are required")

    subject = "Your Verification OTP"
    message = (
        f"Your OTP is: {otp}\n\n"
        "This OTP is valid for a limited time.\n"
        "Do not share it with anyone."
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except BadHeaderError:
        raise ValueError("Invalid email header detected")
    except Exception:
        # Let caller handle this
        raise RuntimeError("Failed to send OTP email")

@never_cache
def verify_otp(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        if not entered_otp.isdigit() or len(entered_otp) != 4:
            messages.error(request, "Invalid OTP format.")
            return redirect("verify_otp")

        saved_otp = request.session.get("otp")
        email = request.session.get("email")
        otp_time_str = request.session.get("otp_last_sent")

        if not all([saved_otp, email, otp_time_str]):
            messages.error(request, "Session expired. Please sign up again.")
            return redirect("account_signup")

        otp_time = parse_datetime(otp_time_str)
        if timezone.now() > otp_time + timedelta(seconds=300):
            messages.error(request, "OTP expired. Please resend.")
            return redirect("verify_otp")

        attempts = request.session.get("otp_attempts", 0)
        if attempts >= 5:
            messages.error(request, "Too many incorrect attempts. Please resend OTP.")
            return redirect("verify_otp")

        if str(entered_otp) != str(saved_otp):
            request.session["otp_attempts"] = attempts + 1
            messages.error(request, "Invalid OTP.")
            return redirect("verify_otp")

        request.session.pop("otp_attempts", None)

        data = request.session.get("signup_data")
        if not data:
            messages.error(request, "Session expired. Please sign up again.")
            return redirect("account_signup")

        try:
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    email=data["email"],
                    username=data.get("username"),
                    password=data["password"],
                )
                user.is_active = True
                user.is_email_vfd = True
                user.save()

                UserProfile.objects.create(user=user)

        except IntegrityError:
            messages.error(request, "Account already exists. Please log in.")
            return redirect("account_login")

        # Clean OTP data safely
        for key in ["otp", "email", "signup_data", "otp_last_sent", "otp_attempts"]:
            request.session.pop(key, None)

        request.session.cycle_key()
        auth_login(request, user)

        messages.success(request, "Account verified successfully!")
        return redirect("home")

    return render(request, "otp.html")


@require_POST
def resend_otp(request):
    if request.user.is_authenticated:
        return redirect("home")

    email = request.session.get("email")
    otp_time_str = request.session.get("otp_last_sent")

    if not email or not otp_time_str:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("account_signup")

    last_sent_time = parse_datetime(otp_time_str)
    if not last_sent_time:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("account_signup")

    # OTP lifetime check
    OTP_LIFETIME = 300  # 5 minutes
    if timezone.now() > last_sent_time + timedelta(seconds=OTP_LIFETIME):
        messages.error(request, "OTP session expired. Please sign up again.")
        return redirect("account_signup")

    # Cooldown check
    COOLDOWN_SECONDS = 60
    if timezone.now() < last_sent_time + timedelta(seconds=COOLDOWN_SECONDS):
        remaining = int(
            (last_sent_time + timedelta(seconds=COOLDOWN_SECONDS) - timezone.now())
            .total_seconds()
        )
        messages.error(request, f"Please wait {remaining} seconds before resending OTP.")
        return redirect("verify_otp")

    # Resend limit
    resend_count = request.session.get("otp_resend_count", 0)
    if resend_count >= 5:
        messages.error(request, "Maximum OTP resend limit reached.")
        return redirect("account_signup")

    # Generate OTP
    otp = secrets.randbelow(9000) + 1000

    # Update session
    request.session["otp"] = otp
    request.session["otp_last_sent"] = timezone.now().isoformat()
    request.session["otp_resend_count"] = resend_count + 1

    # Reset attempts
    request.session.pop("otp_attempts", None)

    try:
        send_otp(email, otp)
    except Exception:
        messages.error(request, "Unable to send OTP. Please try again later.")
        return redirect("verify_otp")

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("verify_otp")


@never_cache
def login(request):
    if request.user.is_authenticated:
        return redirect("home")

    next_url = request.GET.get("next") or request.POST.get("next")

    # Lockout config
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300  # 5 minutes

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, "login.html")

        # Brute-force protection
        attempts = request.session.get("login_attempts", 0)
        last_attempt = request.session.get("last_login_attempt")

        if attempts >= MAX_ATTEMPTS and last_attempt:
            last_time = parse_datetime(last_attempt)
            if last_time and timezone.now() < last_time + timedelta(seconds=LOCKOUT_SECONDS):
                messages.error(request, "Too many failed attempts. Try again later.")
                return render(request, "login.html")
            else:
                request.session.pop("login_attempts", None)

        user = authenticate(request, email=email, password=password)

        if user is None:
            request.session["login_attempts"] = attempts + 1
            request.session["last_login_attempt"] = timezone.now().isoformat()
            messages.error(request, "Invalid email or password.")
            return render(request, "login.html")

        if not user.is_active:
            messages.error(request, "Please verify your email first.")
            return render(request, "login.html")

        # Secure login
        request.session.cycle_key()
        auth_login(request, user)

        request.session.pop("login_attempts", None)
        request.session.pop("last_login_attempt", None)

        if user.is_staff or user.is_superuser:
            return redirect("/admin/")

        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        messages.success(request, "Logged in successfully.")
        return redirect("home")

    return render(request, "login.html")


@require_POST
@never_cache
def user_logout(request):
    # Completely clear session
    request.session.flush()

    # Logout user
    logout(request)

    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


@never_cache
@login_required
def profile(request):
    if request.user.is_staff:
        return redirect('/admin_user/')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    return render(request, 'user_profile.html', {
        'profile': profile,
        'addresses': addresses,
        'default_address': default_address,
        'wallet': wallet,   
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
    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        if not email:
            messages.error(request, "Please enter a valid email address.")
            return redirect("forgot_password")

        # rate limiting
        last_request = request.session.get("pwd_reset_last")
        if last_request:
            last_time = parse_datetime(last_request)
            if last_time and now() < last_time + timedelta(seconds=60):
                messages.error(request, "Please wait before requesting again.")
                return redirect("forgot_password")

        request.session["pwd_reset_last"] = now().isoformat()

        try:
            user = User.objects.get(email=email)

            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = (
                f"{request.scheme}://{request.get_host()}"
                f"{reverse('new_password', kwargs={'uidb64': uidb64, 'token': token})}"
            )

            send_mail(
                subject="Reset your password",
                message=f"Click the link to reset your password:\n\n{reset_link}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

        except User.DoesNotExist:
            pass

        messages.success(
            request,
            "If an account exists with this email, a reset link has been sent."
        )
        return redirect("forgot_password")

    return render(request, "forgot.html")


@never_cache
def new_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Password reset link is invalid or expired.")
        return redirect("account_login")

    if request.method == "POST":
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not new_password or not confirm_password:
            messages.error(request, "Both password fields are required.")
            return render(request, "new_pass.html")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "new_pass.html")

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render(request, "new_pass.html")

        # Rotate sessions & invalidate old ones
        request.session.flush()

        user.set_password(new_password)
        user.save(update_fields=["password"])

        messages.success(
            request,
            "Password updated successfully. Please log in with your new password."
        )
        return redirect("account_login")

    return render(request, "new_pass.html")
