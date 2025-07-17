from django.shortcuts import render,redirect,get_object_or_404
from ecomusers.models import User
from django.contrib.auth import authenticate,login,logout,get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings
import random
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from allauth.socialaccount.models import SocialToken # GOOGLE AUTHENTICATION
import requests

# VIEWS FOR USER AUTHENTICARION AND AUTHERISATION.


#User Registration
@never_cache
def registerview(request):
    
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        print(f'name: {name} email: {email} phone: {phone} password: {password}')
        
        if password != confirm_password:
            messages.error(request,'Password do not matching.')
            return render(request, 'user/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request,'Email Already Registered.')
            return render(request, 'auth/register.html')
        
        # CREATION OF OTP
        otp=''.join([str(random.randint(0,9)) for _ in range(6) ])
        # TIME FOR OTP       
        expiry_time= timezone.now() + timedelta(seconds=120)
        request.session['expiry_time'] = expiry_time.isoformat()
        
        print(f'Generated otp is {otp}')
        
        # SENDING EMAIL
        subject='OTP for MediKate Email Verification'
        message=f'The OTP for the MediKate verification: {otp} \n Enter this for the successful verification. '
        from_email=settings.DEFAULT_FROM_EMAIL
        recipient_list=[email]

        try:
            send_mail(subject,message,from_email,recipient_list,fail_silently=False)
            print(f'Email sent to {email}.')
           
        except Exception as e:
            print(f'Email send failed. {e}')
            messages.error(request,'Failed to send OTP. Please Try again.')
            return render(request,'auth/register.html')
        
        # STORING USER CREDENTIALS IN SESSION
        request.session['name']=name
        request.session['email']=email
        request.session['phone']=phone
        request.session['password']=password
        request.session['otp']=otp
        request.session.modified=True
        print(request.session['name'])
    
    # REDIRECTS TO OTP VERIFICATION
        messages.success(request,'OTP sent to your mail successfully.')
        return redirect('otp_verify')
         
    
    return render(request, 'auth/register.html')

# VIEWS FOR OTP VERIFICATION OF THE USER
@never_cache
def otp_verify_view(request):
    # ACTION OF VERIFY OTP BUTTON
    if request.method=='POST':
        
        entered_otp=request.POST.get('otp')
        otp_method=request.POST.get('otp_method')
         # TIME FOR OTP
        verify_time=timezone.now() 
        expiry_time_str = request.session.get('expiry_time')
        expiry_time = parse_datetime(expiry_time_str)
        if verify_time > expiry_time:
            del request.session['otp']

        stored_otp=request.session.get('otp')
        name= request.session.get('name')
        email= request.session.get('email')
        phone= request.session.get('phone')
        password= request.session.get('password')
        print(f'name: {name}, email: {email}, phone: {phone} password: {password}')
       
        if not name or not stored_otp or not email:
             messages.error(request,'Session has expired. Please try again.')
             return render(request,'auth/otpverify.html')
        if otp_method != 'email':
            messages.error(request,'OTP is sending via Email. Please select Email as method.')
            return render(request,'auth/otpverify.html')
        # USER DATA STORING.
        if entered_otp == stored_otp:
            user= User.objects.create_user(
                username=name,
                email=email,
                password=password
            )
            user.first_name=name
            user.phone=phone
            user.save()
            # REMOVING SESSION DATA
            
            del request.session['otp']
            del request.session['name']
            del request.session['email']
            del request.session['phone']
            del request.session['password']
            request.session.modified =True
            messages.success(request,'OTP verified and Account created successfully.')
            
            return redirect('login')
        else:
            messages.error(request,'Invalid OTP. Please try again.')
            return render(request,'auth/otpverify.html')
    
    return render(request,'auth/otpverify.html')

# VIEW FOR RESEND OTP BUTTON
@never_cache
def resend_otp_view(request):
    if request.method=='POST':
        otp_method=request.POST.get('otp_method')
        name=request.session.get('name')
        email=request.session.get('email')
        phone=request.session.get('phone')
        password=request.session.get('password')

        if not name or not email:
            messages.error(request,'Session has expired. Please try again.')
            return render(request,'auth/otpverify.html')
        if otp_method !='email':
            messages.error(request,'OTP is sending via Email. Please select Email as method.')
            return render(request,'auth/otpverify.html')

        # GENERATION OF NEW OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        print(f'Resend OTP is {otp}')
        # TIME FOR OTP
        expiry_time=timezone.now() + timedelta(seconds=120)
        request.session['expiry_time']= expiry_time.isoformat()

        # EMAIL SENDING
        subject=f'OTP for MediKate (Resend).'
        message=f'New OTP for MediKate verification is {otp}.\n Please enter the otp for verification. '
        from_email=settings.DEFAULT_FROM_EMAIL
        recipient_list=[email]

        try:
            send_mail(subject,message,from_email,recipient_list)
        except Exception as e:
            messages.error(request,'Failed to send Email. Try again.')
            return render(request,'auth/otpverify.html')
        # OTP UPDATING IN THE SESSION.
        request.session['otp']=otp
        request.session.modified= True
        
        messages.info(request,f'OTP  has Resent successfully to {email}. Please check your mail.')
        return render(request,'auth/otpverify.html')    
    
    return render(request,'auth/otpverify.html')


# VIEW FOR FORGOT PASSWORD
@never_cache
def forgot_password_view(request):
    if request.method=='POST':
        email=request.POST.get('email')
        # CHECKING EMAIL EXISTING
        if not User.objects.filter(email=email).exists():
            messages.error(request,'A user with this email account does not exists.')
            return redirect('forgot_password')
        # GENERATE OTP
        otp=str(random.randint(100000,999999))
        # OTP TIME
        expiry_time=timezone.now() + timedelta(seconds=120)
        print(f'Generated otp for Forgot Password is {otp}')

        # SESSION UPDATE
        request.session['reset_email']=email
        request.session['reset_otp']=otp
        request.session['expiry_time']=expiry_time.isoformat()

        # SENDING EMAIL
        subject='OTP for Password Reset'
        message=f'OTP for Password reset is {otp}.\n Enter the otp for create new password.'
        from_mail=settings.DEFAULT_FROM_EMAIL
        recipient_list=[email]

        try:
            send_mail(subject,message,from_mail,recipient_list)
        except Exception as e:
            print(f'error is {e}')
            messages.error(request,f'Failed to send Email. Try again.')
            return render(request,'auth/forgot_password.html')
        messages.success(request,f'OTP has sent to {email} successfully. Please check your mail.')
        return redirect('reset_password')    
    
    return render(request,'auth/forgot_password.html')

# VIEW FOR NEW PASSWORD AND CONFIRMATION
@never_cache
def reset_password_view(request):
    if request.method =='POST':
        new_password=request.POST.get('new_password')
        confirm_password=request.POST.get('confirm_password')
        entered_otp=request.POST.get('otp')

        email=request.session.get('reset_email')
        stored_otp=request.session.get('reset_otp')
        expiry_str=request.session.get('expiry_time')

        if not email or not stored_otp or not expiry_str:
            messages.error(request,'Session has expired. Try again.')
            return redirect('reset_password')

        # OTP TIME
        expiry_time=parse_datetime(expiry_str)
        if timezone.now() > expiry_time:
            request.session.pop('reset_otp', None) 
            messages.error(request,'OTP has expired. Try again.')

            return redirect('reset_password')

        if entered_otp != stored_otp:
            messages.error(request,'Invalid OTP. Try again.')

            return redirect('reset_password')

        if new_password != confirm_password:
            messages.error(request,'Password does not match. Try again.')

            return redirect('reset_password')
        
        
        user = get_object_or_404(User, email=email)
        try:
            validate_password(new_password,user)
        except Exception as e:
            for error in e.messages:
                messages.error(request,error)
            return redirect('reset_password')
        user.set_password(new_password)
        user.save()
        # SESSION CLEAR
        for key in ['reset_email','reset_otp','expiry_time']:
            request.session.pop(key,None)
        messages.success(request,'New Password set successfully.')
        return redirect('login')
        

    return render(request,'auth/reset_password.html')       

# RESEND OTP FOR PASSWORD RESET
@never_cache
def resend_password_otp_view(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')

        if not email or not User.objects.filter(email=email).exists():
            messages.error(request,'User does not exists.')
            return redirect('forgot_password')

        otp = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(seconds=120)
        # to show otp in the terminal
        print(f'Resend otp  for Reset Password is {otp}')

        request.session['reset_otp'] = otp
        request.session['expiry_time'] = expiry_time.isoformat()

        subject = 'Redent OTP for Password Reset'
        message = f'New OTP for password reset is {otp}.'
        from_mail = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(subject, message, from_mail, [email])
        except Exception as e:
            print(f'email send error: {e}')
            messages.error(request,'Failed to resend OTP. Try again.')
            return redirect('reset_password')
        
        messages.success(request,f'OTP has resent successfully to {email}')
        return redirect('reset_password')
    return redirect('forgot_password')


# Usre Login
@never_cache
def loginview(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return redirect('login')

        user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            login(request, user)
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['email'] = user.email
            request.session.set_expiry(3600)

            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('login_home')
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, 'auth/login.html')

    return render(request, 'auth/login.html')

# VIEW FOR LOGOUT


@never_cache
@login_required
def logout_view(request):
    # Get the user's Google token
    try:
        social_token = SocialToken.objects.get(account__user=request.user, account__provider='google')
        token = social_token.token
        # Revoke the token via Google's API
        print(token)
        requests.post('https://accounts.google.com/o/oauth2/revoke', params={'token': token})
    except SocialToken.DoesNotExist:
        pass
    request.session.flush()  # REMOVING SESSION DATA AFTER USER LOGOUT

    logout(request)
    return redirect('login')

# -----------------------------------------------------------------------------------------------------------------------------

# ADMIN AUTHENTICATION AND AUTHORISATION
from .decorators import superuser_required

# VIEW FOR ADMIN LOGIN 
@never_cache
def admin_login_view(request):
    if request.method=='POST':
        username=request.POST.get('username')
        password=request.POST.get('password')

        user=authenticate(request,username=username,password=password)

        if user is not None and user.is_superuser:
            
            login(request,user)

            return redirect('admin_dashboard')
        else: messages.error(request,'Invalid Credentials or Not an admin.')

    return render(request,'auth/admin_login.html')



# VIEW FOR ADMIN DASHBOARD
@superuser_required
@never_cache
def admin_dashboard_view(request):
    
    return render(request,'admin/dashboard.html')


# VIEW FOR ADMIN LOGOUT
@superuser_required
@never_cache
def admin_logout_view(request):

    logout(request)
    return redirect(admin_login_view)







