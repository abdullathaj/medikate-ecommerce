from django.shortcuts import render,redirect
from ecomusers.models import User
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings
import random
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime

# VIEWS FOR USER AUTHENTICARION AND AUTHERISATION.


#User Registration
def registerview(request):
    
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        print(f'name: {name} email: {email} phone: {phone} password: {password}')
        
        if password != confirm_password:
            return render(request, 'user/register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=email).exists():
            return render(request, 'auth/register.html', {'error': 'Email already registered'})
        
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
            return render(request,'auth/register.html',{'error':'Failed to send the OTP. Please try again.'})
        
        # STORING USER CREDENTIALS IN SESSION
        request.session['name']=name
        request.session['email']=email
        request.session['phone']=phone
        request.session['password']=password
        request.session['otp']=otp
        request.session.modified=True
        print(request.session['name'])
    
    # REDIRECTS TO OTP VERIFICATION
        return redirect('otp_verify') 
    
    return render(request, 'auth/register.html')

# VIEWS FOR OTP VERIFICATION OF THE USER

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
             return render(request,'auth/otpverify.html',{'error':'Session has expired. Please register again.'})
        if otp_method != 'email':
            return render(request,'auth/otpverify.html',{'error':'OTP is sending via Email. Please select Email as method.'})
        # USER DATA STORING.
        if entered_otp == stored_otp:
            user= User.objects.create_user(
                username=email,
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
            
            return redirect('login')
        else:
            return render(request,'auth/otpverify.html',{'error':'Inavalid OTP. Please try again.'})
    
    return render(request,'auth/otpverify.html')

# VIEW FOR RESEND OTP BUTTON
def resend_otp_view(request):
    if request.method=='POST':
        otp_method=request.POST.get('otp_method')
        name=request.session.get('name')
        email=request.session.get('email')
        phone=request.session.get('phone')
        password=request.session.get('password')

        if not name or not email:
            return render(request,'auth/otpverify.html',{'error':'Session has expired. Please register again.'})
        if otp_method !='email':
            return render(request,'auth/otpverify.html',{'error':'OTP is sending via Email. Please select Email method. '})

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
            return render(request,'auth/otpverify.html',{'error':'Failed to send Email. Try again.'})
        # OTP UPDATING IN THE SESSION.
        request.session['otp']=otp
        request.session.modified= True
        return render(request,'auth/otpverify.html',{'success':f'OTP successfully resent to {email}'})    
    
    return render(request,'auth/otpverify.html')


# VIEW FOR FORGOT PASSWORD
def forgot_password_view(request):
    if request.method=='POST':
        email=request.POST.get('email')
        # CHECKING EMAIL EXISTING
        if not User.objects.filter(username=email).exists():
            return render(request,'auth/forgot_password.html',{'error':'A user with this email account does not exist.'})
        # GENERATE OTP
        otp=str(random.randint(100000,999999))
        # OTP TIME
        expiry_time=timezone.now() + timedelta(seconds=120)
        print(f'Generated otp is {otp}')

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
            return render(request,'auth/forgot_password.html',{'error':'Failed to send Email. Try again.'})
        
        return redirect('reset_password')    
    
    return render(request,'auth/forgot_password.html')

# VIEW FOR NEW PASSWORD AND CONFIRMATION

def reset_password_view(request):
    if request.method =='POST':
        new_password=request.POST.get('new_password')
        confirm_password=request.POST.get('confirm_password')
        entered_otp=request.POST.get('otp')

        email=request.session.get('reset_email')
        stored_otp=request.session.get('reset_otp')
        expiry_str=request.session.get('expiry_time')

        if not email or not stored_otp or not expiry_str:
            return render(request,'auth/reset_password.html',{'error':'Session has expired.Try again.'})

        # OTP TIME
        expiry_time=parse_datetime(expiry_str)
        if timezone.now() > expiry_time:
            request.session.pop('reset_otp', None) 
            return render(request,'auth/reset_password.html',{'error':'OTP has expired.Try again.'})

        if entered_otp != stored_otp:
            return render(request,'auth/reset_password.html',{'error':'Invalid OTP. Try again.'})

        if new_password != confirm_password:
            return render(request,'auth/reset_password.html',{'error':'Passwords does not match.Try again.'})
        
        try:
            user=User.objects.get(username=email)
            user.set_password(new_password)
            user.save()
            # SESSION CLEAR
            for key in ['reset_email','reset_otp','expiry_time']:
                request.session.pop(key,None)
            return redirect('login')
        except User.DoesNotExist:
             return render(request,'auth/reset_password.html',{'error':'User does not Exist.'})

    return render(request,'auth/reset_password.html')       

# RESEND OTP FOR PASSWORD RESET

def resend_password_otp_view(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')

        if not email or not User.objects.filter(username=email).exists():
            return redirect('forgot_password')

        otp = str(random.randint(100000, 999999))
        expiry_time = timezone.now() + timedelta(seconds=120)
        # to show otp in the terminal
        print(f'Resend otp is {otp}')

        request.session['reset_otp'] = otp
        request.session['expiry_time'] = expiry_time.isoformat()

        subject = 'OTP for Password Reset (Resent)'
        message = f'New OTP for password reset is {otp}.'
        from_mail = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(subject, message, from_mail, [email])
        except Exception as e:
            return render(request, 'auth/reset_password.html', {'error': 'Failed to resend OTP.'})

        return render(request, 'auth/reset_password.html', {'success': 'OTP resent successfully'})
    return redirect('forgot_password')


# Usre Login
def loginview(request):
    if request.method == 'POST':
        name =request.POST['username']
        password = request.POST['password']
        print(name)
        print(password)

        
        user = authenticate(request,username= name,password=password)
        print(user)
    


        if user is not None:
            login(request,user)
            return redirect('login_home')
        else:
            return render(request,'auth/login.html')

    return render(request, 'auth/login.html')

# VIEW FOR LOGOUT
@never_cache
def logout_view(request):
    logout(request)
    return redirect('login')

# -----------------------------------------------------------------------------------------------------------------------------

# ADMIN AUTHENTICATION AND AUTHORISATION
from .decorators import superuser_required

# VIEW FOR ADMIN LOGIN 
def admin_login_view(request):
    if request.method=='POST':
        username=request.POST.get('username')
        password=request.POST.get('password')

        user=authenticate(request,username=username,password=password)

        if user is not None and user.is_superuser:
            login(request,user)

            return redirect('admin_dashboard')
        else: messages.error('Invalid Credentials or Not an admin.')

    return render(request,'auth/admin_login.html')



# VIEW FOR ADMIN DASHBOARD
@superuser_required
@never_cache
def admin_dashboard_view(request):

    return render(request,'admin/dashboard.html')


# VIEW FOR ADMIN LOGOUT
@never_cache
def admin_logout_view(request):

    logout(request)
    return redirect(admin_login_view)







