from django.shortcuts import render,redirect,get_object_or_404
from django.http import Http404,JsonResponse
import json
from django.db import IntegrityError,transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import UserAddress,User,WishlistProducts,CartProducts,Wallet,Referral,WalletTransaction
from ecomproducts.models import Product,ProductVariant,ProductImage,Categories,Coupon
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Min,Q,F,Sum,FloatField,Prefetch
from .forms import UserProfileForm,UserAddressForm,UserPasswordChangeForm,EmailChangeForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from datetime import timedelta,datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from decimal import Decimal
from django.contrib.auth import update_session_auth_hash
import random

# Create your views here.
# -------------------------------------------------------------------------
# HOME PAGE BEFORE AND AFTER LOGIN AND PRODUCT LIST AND PRODUCT DETAILS
# -------------------------------------------------------------------------

def userhomeview(request):

    active_variant_prefetch= Prefetch('product_variant',queryset=ProductVariant.objects.filter(is_active=True),
                                                                            to_attr='active_variants')
    
    products = (Product.objects.filter(product_variant__is_active= True, category__is_active= True)
                .select_related('category')
                .prefetch_related(active_variant_prefetch)
                .order_by('-created_at').distinct()[:8]
                ) 
    trending_products=products[:8]
    print(f'trending products: {trending_products}')
    
    return render(request, 'auth/home.html',{'products': products, 'trending_products':trending_products})

@login_required(login_url='login') 
@never_cache
def home_after_login(request):
    
    active_variant_prefetch = Prefetch('product_variant', queryset=ProductVariant.objects.filter(is_active=True), to_attr='active_variants'      
    )

    products = (Product.objects.filter(product_variant__is_active=True,category__is_active=True,)
        .select_related('category')
        .prefetch_related(active_variant_prefetch)
        .order_by('-created_at').distinct()[:8]
    )

    wishlist_variant_ids= []
    if request.user.is_authenticated:
        wishlist_variant_ids= WishlistProducts.objects.filter(
            user= request.user
        ).values_list('variant_id', flat= True)
    
    trending_products=products[:8]

    print(f'latest products: {trending_products}')
    print(f'wishlist IDs: {wishlist_variant_ids}')
   
    return render(request,'auth/home.html',{'products':products,'trending products':trending_products,
                                            'wishlist_variant_ids':wishlist_variant_ids})

def product_details(request, variant_id):
    ''' Showing Details of a Product, Related Products and Bread Crumbs'''

    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True, product__category__is_active=True)
    product=variant.product
    print(f'Details of {product}')
    
    variants = product.product_variant.filter(is_active=True)
    wishlist_variant_ids=[]
    if request.user.is_authenticated:
        wishlist_variant_ids= WishlistProducts.objects.filter(
            user= request.user
        ).values_list('variant_id',flat=True)
    print(f'Wishlist IDs: {wishlist_variant_ids}')

    related_products = Product.objects.filter(
        category=product.category,
        product_variant__is_active=True,
        category__is_active=True
    ).exclude(id=product.id).distinct()[:4]
    print(f'Related Products of {product}: {related_products}')

    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Products', 'url': 'product_listing'},
        {'name': 'Product Details', 'url': ''}
    ]
    print(f'Breadcrumbs: {breadcrumbs}')
    context = {
        'product': product,
        'selected_variant':variant,
        'variants': variants,
        'related_products': related_products,
        'wishlist_variant_ids': wishlist_variant_ids,
        'breadcrumbs': breadcrumbs
    }

    return render(request, 'user/product_details.html', context)

def user_product_listing(request):
    ''' Product listing page, Pagination added with 12 products in each page, Get all active categories for filter options
    Get distinct brands for filter options  Apply price range filter Search functionality 
    Wishlist button glowing '''

    variants = ProductVariant.objects.filter(
        is_active=True,
        product__category__is_active=True
    ).select_related('product', 'product__category').prefetch_related('product__product_image').order_by('product__created_at')

    
    query=request.GET.get('q','').strip()
    if query:
        variants=variants.filter(
            Q(product__name__icontains=query) |
            Q(product__category__name__icontains=query) |
            Q(product__brand__icontains=query) |
            Q(product__description__icontains=query)|
            Q(product__category__description__icontains=query)
        )
    wishlist_variant_ids= []
    if request.user.is_authenticated:
        wishlist_variant_ids= WishlistProducts.objects.filter(
            user= request.user
        ).values_list('variant_id',flat=True)

    categories = Categories.objects.filter(is_active=True)

    brands = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).exclude(brand__isnull=True).values_list('brand', flat=True).distinct().order_by('brand')

 
    selected_categories = request.GET.getlist('category')
    selected_brands = request.GET.getlist('brand')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    if selected_categories:
        variants = variants.filter(product__category__id__in=selected_categories)

    if selected_brands:
        variants = variants.filter(product__brand__in=selected_brands)

    if price_min:
        try:
            price_min = float(price_min)
            variants = variants.filter(price__gte=price_min)
        except ValueError:
            pass  
    if price_max:
        try:
            price_max = float(price_max)
            variants = variants.filter(price__lte=price_max)
        except ValueError:
            pass  


    sort = request.GET.get('sort')
    if sort == 'price_low':
        variants = variants.order_by('price')
    elif sort == 'price_high':
        variants = variants.order_by('-price')
    elif sort == 'name_asc':
        variants = variants.order_by('product__name', 'variant_name')
    elif sort == 'name_desc':
        variants = variants.order_by('-product__name', '-variant_name')

    paginator = Paginator(variants, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()

    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Products', 'url': ''}
    ]

    context = {
        'variants': page_obj,
        'categories': categories,
        'brands': brands,
        'selected_categories': selected_categories,
        'selected_brands': selected_brands,
        'price_min': price_min,
        'price_max': price_max,
        'sort': sort,
        'query_string': query_string,
        'query': query,
        'breadcrumbs': breadcrumbs,
        'wishlist_variant_ids': wishlist_variant_ids,
    }

    return render(request, 'user/product_listing.html', context)


# -----------------------------------------------------------------
# USER PROFILE DETAILS, ADDRESS MANAGEMENT ADD EDIT AND DELETE
# -----------------------------------------------------------------
@login_required(login_url='login') 
def users_profile_page(request):
    ''' RENDERING USERS PROFILE PAGE CONTAIN USER DETAILS AND ADDRESSES, REFERRALS ETC.'''
    if not request.user.is_active:
        return redirect('login')
    if not request.user.referral_code:
        request.user.save()
    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Profile', 'url': ''}
    ]
    context={
        'user': request.user,
        'referrals': request.user.referral_made.all(),
        'referral_count': request.user.referral_made.count(),
        'breadcrumbs': breadcrumbs
    } 
    return render(request,'user/profile_page.html',context)

@never_cache
@login_required(login_url='login') 
def user_delete_address(request, address_id):
    ''' TO DELETE CURRENT ADDRESSES '''
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    print(f'Deleting Address: {address}')
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('user_profile_page')

@never_cache
@login_required(login_url='login') 
def users_profile_update_page(request):
    ''' TO UPDATE THE USER PROFILE AS EDIT USER DETAILS, ADD NEW ADDRESSES, CHANGE EMAIL AND CHANGE PASSWORD '''
    user = request.user
    user_form = UserProfileForm(instance=user)
    address_form = UserAddressForm(initial={'user': user})
    password_form=UserPasswordChangeForm(user=user)
    email_form=EmailChangeForm()

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user_form = UserProfileForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                print(f"{user} updated Profile.")
                messages.success(request, "Profile updated.")
                return redirect('user_profile_page')

        elif 'update_address' in request.POST:
            address_form = UserAddressForm(request.POST)
            address_form.initial['user'] = user  
            address_form.instance.user = user   

            if address_form.is_valid():
                address_form.save()
                print(f'{user} is Created new Address.')
                messages.success(request, "Address saved.")
                return redirect('user_profile_page')
            
        elif 'update_password' in request.POST:
            password_form = UserPasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user) 
                print(f'{user} updated Password.')
                messages.success(request, "Password updated successfully.")
                return redirect('user_profile_page')
            else:
                for field, error_list in password_form.errors.items():
                    for error in error_list:
                        print(error)
                        messages.error(request, f"{password_form.fields[field].label}: {error}")
        
        elif 'request_email_otp' in request.POST:
            email_form=EmailChangeForm(request.POST)
            if email_form.is_valid():
                new_email=email_form.cleaned_data['new_email']
                otp=str(random.randint(100000,999999))
                expiry_time=timezone.now() + timedelta(seconds=60)
                
                request.session['change_email']= new_email
                request.session['email_otp']= otp
                request.session['email_expiry_time']= expiry_time.isoformat()
                print(f'OTP for {new_email} : {otp}')

                subject='OTP for Email Change.'
                message=f'Dear {user},\n\n OTP for email verification for email change is {otp}.\n\n Best Regards,\n\n Team MediKate.'
                from_mail=settings.DEFAULT_FROM_EMAIL
                recipient_list=[new_email]

                try:
                    send_mail(subject,message,from_mail,recipient_list)
                    messages.success(request,f'OTP sent to your given email.\n Plese check it.')
                    return redirect('verify_email_otp')
                
                except Exception as e:
                    print(f'error occured as: {str(e)}')
                    messages.error(request,f'Email couldnt sent. Something went wrong.\n Try again.')
                    return redirect('user_profile_update')

    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Profile', 'url': 'user_profile_page'},
        {'name': 'Profrle updation', 'url': ''}
    ]
    context= {
        'user_form': user_form,
        'address_form': address_form,
        'password_form':password_form,
        'email_form': email_form,
        'breadcrumbs': breadcrumbs}
    
    return render(request, 'user/profile_edit.html', context)

@never_cache
@login_required(login_url='login')
def verify_email_otp(request):
    ''' OTP VERIFICATION FOR CHANGE EMAIL '''
    if request.method=='POST':
        entered_otp= request.POST.get('otp')
        new_email=request.session.get('change_email')
        stored_otp= request.session.get('email_otp')
        expiry_str= request.session.get('email_expiry_time')

        if not new_email or not stored_otp or not expiry_str:
            messages.error(request,f'Session has expired. Please try again.')
            print('Session has expired. ')
            return redirect('user_profile_update')
        if stored_otp != entered_otp:
            messages.error(request,f'The OTP is not correct. Try again.')
            print('Entered Incorrect OTP.')
            return redirect('user_profile_update')
        expiry_time= parse_datetime(expiry_str)
        if timezone.now() > expiry_time:
            request.session.pop('change_email',None)
            request.session.pop('email_otp',None)
            request.session.pop('email_expiry_time', None)
            print('Session time for OTP has expired.')
            messages.error(request,f'OTP has expired.Please try again.')
            return redirect('user_profile_update')
        user= request.user
        user.email= new_email
        user.save()
        print(f'The changed Email for {user} is {new_email}.')

        for i in ['change_email','email_otp','email_expiry_time']:
            request.session.pop(i,None)
        messages.success(request,f'The email is updated to {new_email} for {user}')
        return redirect('user_profile_page')
    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Profile', 'url': 'user_profile_page'},
        {'name': 'Profile updation', 'url': 'user_profile_update'},
        {'name': 'Emai verification', 'url': ''}
    ]
        
    return render(request,'user/verify_email_otp.html',{'breadcrumbs': breadcrumbs})

@never_cache
@login_required(login_url='login')
def user_edit_address(request, address_id):
    ''' EDIT CURRENT USER ADDRESS '''
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    print(f'Editing Address is: {address}')
    if request.method == 'POST':
        form = UserAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            print(f'Address changed to: {address}')
            messages.success(request, "Address updated successfully.")
            return redirect('user_profile_page')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = UserAddressForm(instance=address)
    
    return render(request, 'user/profile_address_edit.html', {
        'form': form,
        'address_id': address_id
    })

#--------------------------------------------------------------------------------------------------
# WISHLIST MANAGEMENT FOR AUTHENTICATED USER ADDING AND REMOVING PRODUCTS, ADDING TO CART
# ------------------------------------------------------------------------------------------------
@never_cache
@login_required(login_url='login') 
def add_to_wishlist(request, variant_id):
    
    variant = get_object_or_404(ProductVariant, id=variant_id,is_active=True)

    # Check if variant is already in user's wishlist
    existing = WishlistProducts.objects.filter(user=request.user, variant=variant).exists()
    if existing:
        print(f'{variant} is ALREADY in wishlist.')
        messages.warning(request, "This item is already in your wishlist.")
    else:
        WishlistProducts.objects.create(user=request.user, variant=variant)
        print(f'{variant} ADDED to wishlist.')
        messages.success(request, f"{variant} added to your wishlist.")

    return redirect(request.META.get('HTTP_REFERER', 'user_wishlist_page'))

@login_required(login_url='login') 
def users_wishlist_page(request):
    """FOR SHOWING THE PRODUCTS IN WISHLIST ADDED BY AUTHENTICATED USER
    """
    if not request.user.is_active:
        return redirect('login')
    
    wishlist_items = WishlistProducts.objects.filter(
        user=request.user,
        variant__is_active=True
    ).select_related('variant__product')    
    
    print(f'{request.user}s wishlist products:\n {wishlist_items}')
    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Wishlist', 'url': ''}
    ]
    return render(request, 'user/wishlist_page.html', {'wishlist_items': wishlist_items, 'breadcrumbs':breadcrumbs})

@login_required(login_url='login')
def move_to_cart(request,variant_id):
    """ MOVING THE PRODUCT TO CART FROM WISHLIST AND REMOVE IT FROM WISHLIST """
    variant= get_object_or_404(ProductVariant, id=variant_id, is_active=True)
   
    
    if variant.stock < 1:
        messages.error(request,f'{variant} is Out of stock.')
    else:
        WishlistProducts.objects.filter(user=request.user, variant= variant).delete()
        cart,created= CartProducts.objects.get_or_create(user=request.user, variant=variant)
        if created:
            messages.success(request, f'{variant.product.name} {variant.variant_name} is added to the cart.')
            print(f'{variant} as Added to Cart from Wishlist.')
        else:
            messages.warning(request, f'{variant.product.name} {variant.variant_name} is already in your cart.')
            print(f'Unable to add {variant} to Cart. Cart already has this product.')
    return redirect('user_wishlist_page')

@never_cache
@login_required(login_url='login') 
def remove_from_wishlist(request):
    variant_id = request.POST.get('variant_id')
    variant = get_object_or_404(ProductVariant, id=variant_id)

    WishlistProducts.objects.filter(user=request.user, variant=variant).delete()
    messages.success(request, f"{variant} removed from your wishlist.")
    print(f'{variant} has Removed from Wishlist.')

    return redirect('user_wishlist_page')


# --------------------------------------------------------------------
# USER CART MANAGEMENT , ADDING PRODUCTS FOR AUTHENTICATED USERS
# ---------------------------------------------------------------------
@never_cache
@login_required(login_url='login')
def add_to_cart(request, variant_id):
    """Adding Product to the Cart using Cart Button. Restricts when Product stock is less than one or
      Product alreadyin the Cart."""
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        
        if variant.stock < 1:
            messages.error(request, f"{variant} is out of stock.")
            return redirect(request.META.get('HTTP_REFERER', 'user_cart_page'))

        if CartProducts.objects.filter(user=request.user, variant=variant).exists():
            messages.warning(request,f'The item {variant} is already in the cart.')
            print(f'{variant} is already in cart.')
        else:
            CartProducts.objects.create(user=request.user, variant=variant, quantity=1)
            messages.success(request,f" the Item {variant} is added to the cart.")
            print(f'{variant} is added to the cart.')

    except IntegrityError:
        messages.error(request,"Something is wrong for adding to the cart. Please try again.")

    except Exception as e:
        messages.error(request,f'Unexpected error : {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'user_cart_page'))

@login_required(login_url='login')
def users_cart_page(request):
    if not request.user.is_active:
        return redirect('login')

    cart_items = CartProducts.objects.filter(
        user=request.user,
        variant__is_active=True,
    ).select_related('variant__product')

    original_total_price = Decimal('0')
    selling_total_price = Decimal('0')
    discount_total = Decimal('0')
    coupon_discount = Decimal('0')
    coupon_applied = None

    cart_item_details = []
    for item in cart_items:
        if item.quantity <1 :
            item.delete()
            continue
        if item.quantity > item.variant.stock or item.variant.stock == 0:
            messages.error(request, f"Insufficient stock for {item.variant}. {item.variant.stock} items available.")
            continue
        if item.quantity > 5:
            item.quantity = 5
            item.save()
            messages.info(request, 'The maximum purchase quantity of same product is limited to 5.')

        # TRUE PRICE OF PRODUCT BEFORE OFFER
        original_item_price = item.quantity * item.variant.original_price 
        # CALCULATED PRICE WHETHER OFFER IS ON OR OFF
        selling_item_price = item.total_price  
        original_total_price += original_item_price
        selling_total_price += selling_item_price
        # THE TOTAL DISCOUNT USER GETS IF ANY DISCOUNT FOR THE PRODUCT
        discount_total += original_item_price - selling_item_price

        # temporarily store without coupon
        cart_item_details.append({
            'variant_id': item.variant.id,
            'quantity': item.quantity,
            'unit_price': str(item.variant.final_price),   # calculated price before coupon
            'item_total': str(item.total_price),
            'item_discount': str(original_item_price - item.total_price)
        })

    #  Apply coupon if present
    if 'applied_coupon' in request.session:
        try:
            coupon = Coupon.objects.get(coupon_code=request.session['applied_coupon'], is_active=True)
            if coupon.is_valid and coupon.minimum_purchase_amount <= selling_total_price:
                coupon_applied = coupon
                coupon_discount = (selling_total_price * Decimal(coupon.discount_percentage) / Decimal(100)).quantize(Decimal('0.01'))
                if coupon_discount > selling_total_price:
                    coupon_discount = selling_total_price

                # 🔑 Distribute discount across cart items proportionally
                distributed_cart_items = []
                for detail in cart_item_details:
                    item_total = Decimal(detail['item_total'])
                    share = (item_total / selling_total_price) if selling_total_price > 0 else Decimal('0')
                    item_discount_share = (coupon_discount * share).quantize(Decimal('0.01'))
                    discounted_total = item_total - item_discount_share
                    discounted_unit_price = (discounted_total / detail['quantity']).quantize(Decimal('0.01'))

                    distributed_cart_items.append({
                        'variant_id': detail['variant_id'],
                        'quantity': detail['quantity'],
                        'unit_price': str(discounted_unit_price),   #  discounted price per unit
                        'item_total': str(discounted_total),       #  total after coupon share
                        'item_discount': str((Decimal(detail['item_discount']) + item_discount_share).quantize(Decimal('0.01')))
                    })

                cart_item_details = distributed_cart_items

            else:
                del request.session['applied_coupon']
        except Coupon.DoesNotExist:
            del request.session['applied_coupon']

    amount_payable = selling_total_price - coupon_discount 

    # Fetch valid coupons
    valid_coupons = Coupon.objects.filter(
        models.Q(is_active=True) &
        models.Q(valid_from__lte=timezone.now()) &
        models.Q(valid_to__gte=timezone.now()) &
        (models.Q(max_usage_limit__gt=models.F('total_usage')) | models.Q(max_usage_limit=0)) &
        models.Q(minimum_purchase_amount__lte=selling_total_price)
    )

    #  Save price breakdown in session (with per-item discounted unit price)
    request.session['cart_price_data'] = {
        'original_total_price': str(original_total_price),
        'selling_total_price': str(selling_total_price),
        'discount_total': str(discount_total),
        'coupon_discount': str(coupon_discount),
        'amount_payable': str(amount_payable),
        'cart_item_details': cart_item_details,
        'applied_coupon': coupon_applied.coupon_code if coupon_applied else None
    }

    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Cart', 'url': ''}
    ]
    context = {
        'cart_items': cart_items,
        'payable_amount': amount_payable,
        'original_total_price': original_total_price,
        'discount_total': discount_total,
        'selling_total_price': selling_total_price,
        'coupon_discount': coupon_discount,
        'coupon_applied': coupon_applied,
        'valid_coupons': valid_coupons,
        'estimated_delivery_date': (datetime.now() + timedelta(days=7)).strftime('%B %d, %Y'),
        'breadcrumbs': breadcrumbs
    }
    return render(request, 'user/cart_page.html', context)

@never_cache
@login_required(login_url='login')
def update_cart_quantity(request, cart_item_id):
    """Increase or decrease cart item quantity with stock validation."""
    try:
        cart_item = get_object_or_404(CartProducts, user=request.user, id=cart_item_id)
        action = request.POST.get('action')

        if action == 'increase':
            if cart_item.quantity >=5:
                messages.warning(request,f'You can only select maximum of 5 products for each product.')
            elif cart_item.quantity  >= cart_item.variant.stock:
                messages.error(request, f"Cannot increase quantity. Stock limit reached.")
            else:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request,f"Quantity updated for {cart_item.variant} as {cart_item.quantity}.")

        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, f"Quantity updated for {cart_item.variant} as {cart_item.quantity}.")
                                        
            else:
                messages.warning(request, "Quantity must be at least 1.")
        else:
            messages.error(request, "Invalid action.")

    except Exception as e:
        messages.error(request, f"Unexpected error occurred: {str(e)}")

    return redirect('user_cart_page')

@never_cache
@login_required(login_url='login') 
def remove_cart_item(request,cart_item_id):
    """ REMOVING AN ITEM FROM THE CART """

    cart_item=get_object_or_404(CartProducts,user=request.user,id=cart_item_id)
    cart_item.delete()

    messages.success(request, f"{cart_item.variant} removed from your cart.")

    return redirect('user_cart_page')

@never_cache
@login_required(login_url='login') 
def save_for_later(request,cart_item_id):

    cart_item=get_object_or_404(CartProducts,user=request.user, id=cart_item_id)
    variant=cart_item.variant

    if WishlistProducts.objects.filter(user=request.user,variant=variant).exists():
        messages.error(request,f'{variant} is already in the wishlist')
    else:
        WishlistProducts.objects.create(user=request.user,variant=variant)
        messages.success(request,f'{variant} is added to the wishlist.')
    
    cart_item.delete()
    
    return redirect('user_cart_page')

@login_required(login_url='login')
def apply_coupon(request):
     if request.method =='POST':
        coupon_code= request.POST.get('coupon_code')
        if coupon_code:
            try:
                coupon=Coupon.objects.get(coupon_code=coupon_code, is_active= True)
                cart_items= CartProducts.objects.filter(user= request.user, variant__is_active=True)
                selling_total_price= sum(item.quantity * item.variant.final_price for item in cart_items)
                if not coupon.is_valid:
                    messages.error(request,f'This is invalid coupon or coupon validity expired.')
                elif Decimal(coupon.minimum_purchase_amount) > Decimal(selling_total_price):
                    messages.error(request,f'Minimum purchase amount of {coupon.minimum_purchase_amount} is required to apply this coupon.')
                elif request.session.get('applied_coupon') == coupon_code:
                    messages.info(request,f'This coupon is already applied.')
                else:
                    request.session['applied_coupon']= coupon_code
                    messages.success(request, f'Coupon {coupon_code} is applied successfully.')
            except Coupon.DoesNotExist:
                messages.error(request,f'This coupon doesn not exist.')
        else:
            messages.warning(request, f'Please select a coupon.')
    
     return redirect('user_cart_page')

@login_required(login_url='login')
def remove_coupon(request):    
    if 'applied_coupon' in request.session:
        del request.session['applied_coupon']
        messages.success(request, 'Coupon removed successfully!')
    return redirect('user_cart_page')

# ----------------------------------------------------------------------------
# USER WALLET PAGE
# ----------------------------------------------------------------------------
@login_required(login_url='login')
@never_cache
def users_wallet_page(request):

    wallet,created=Wallet.objects.get_or_create(user=request.user)
    transactions= wallet.transactions.all().order_by('created_at')
    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Wallet', 'url': ''}
    ]
    return render(request,'user/wallet_page.html',{'wallet':wallet, 'transactions':transactions, 'breadcrumbs': breadcrumbs})