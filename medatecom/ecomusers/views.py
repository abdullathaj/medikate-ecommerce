from django.shortcuts import render,redirect,get_object_or_404
from django.http import Http404,JsonResponse
import json
from django.db import IntegrityError,transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import UserAddress,User,WishlistProducts,CartProducts
from ecomproducts.models import Product,ProductVariant,ProductImage,Categories
from django.core.paginator import Paginator
from django.db.models import Min,Q,F,Sum,FloatField
from .forms import UserProfileForm,UserAddressForm,UserPasswordChangeForm
from django.contrib import messages
from datetime import timedelta,datetime
from decimal import Decimal
from django.contrib.auth import update_session_auth_hash

# Create your views here.
# home page for User BEFORE LOGIN

def userhomeview(request):
     # Fetch active products with related category and filter active variants
    products = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).select_related('category').order_by('-created_at').distinct()[:4]
    print(products)

    trending_products=products[:4]

    
    return render(request, 'auth/home.html',{'products': products, 'trending_products':trending_products})


@login_required(login_url='login') # REDIRECT TO LOGIN PAGE FOR UNAUTHENTICATED USERS.
@never_cache
def home_after_login(request):
    
    products = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).select_related('category').order_by('-created_at').distinct()[:4]
    print(products)
    trending_products=products[:4]

    
   

   

    return render(request,'auth/home.html',{'products':products,'trending products':trending_products})

# PRODUCT DETAILING PAGE
def product_details(request, variant_id):
    # Fetch the product
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True, product__category__is_active=True)
    product=variant.product

    # Fetch active variants for the product
    variants = product.product_variant.filter(is_active=True)

    # Fetch related products (same category, excluding current product, up to 4)
    related_products = Product.objects.filter(
        category=product.category,
        product_variant__is_active=True,
        category__is_active=True
    ).exclude(id=product.id).distinct()[:4]

    # Context for template
    context = {
        'product': product,
        'selected_variant':variant,
        'variants': variants,
        'related_products': related_products,
    }

    return render(request, 'user/product_details.html', context)

# PRODUCT LISTING VIEW

def user_product_listing(request):
    # Base queryset for active variants
    variants = ProductVariant.objects.filter(
        is_active=True,
        product__category__is_active=True
    ).select_related('product', 'product__category').prefetch_related('product__product_image').order_by('product__created_at')

    # PRODUCT SEARCH FEATURE
    query=request.GET.get('q','').strip()
    if query:
        variants=variants.filter(
            Q(product__name__icontains=query) |
            Q(product__category__name__icontains=query) |
            Q(product__brand__icontains=query) |
            Q(product__description__icontains=query)|
            Q(product__category__description__icontains=query)
        )


    # Get all active categories for filter options
    categories = Categories.objects.filter(is_active=True)

    # Get distinct brands for filter options
    brands = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).exclude(brand__isnull=True).values_list('brand', flat=True).distinct().order_by('brand')

    # Filtering
    selected_categories = request.GET.getlist('category')
    selected_brands = request.GET.getlist('brand')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    # Apply category filter
    if selected_categories:
        variants = variants.filter(product__category__id__in=selected_categories)

    # Apply brand filter
    if selected_brands:
        variants = variants.filter(product__brand__in=selected_brands)

    # Apply price range filter
    if price_min:
        try:
            price_min = float(price_min)
            variants = variants.filter(price__gte=price_min)
        except ValueError:
            pass  # Ignore invalid price_min
    if price_max:
        try:
            price_max = float(price_max)
            variants = variants.filter(price__lte=price_max)
        except ValueError:
            pass  # Ignore invalid price_max

    # Sorting
    sort = request.GET.get('sort')
    if sort == 'price_low':
        variants = variants.order_by('price')
    elif sort == 'price_high':
        variants = variants.order_by('-price')
    elif sort == 'name_asc':
        variants = variants.order_by('product__name', 'variant_name')
    elif sort == 'name_desc':
        variants = variants.order_by('-product__name', '-variant_name')

    # Pagination
    paginator = Paginator(variants, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build query string for pagination (excluding page parameter)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()

    # Context for template
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
        'query': query
    }

    return render(request, 'user/product_listing.html', context)



# USER PROFILE DETAILS, ADDRESS MANAGEMENT ADD EDIT AND DELETE

@login_required(login_url='login') 
def users_profile_page(request):
    if not request.user.is_active:
        return redirect('login')
   
    return render(request,'user/profile_page.html')

@never_cache
@login_required(login_url='login') 
def user_delete_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('user_profile_page')

@never_cache
@login_required(login_url='login') 
def users_profile_update_page(request):
    user = request.user
    user_form = UserProfileForm(instance=user)
    address_form = UserAddressForm(initial={'user': user})
    password_form=UserPasswordChangeForm(user=user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user_form = UserProfileForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Profile updated.")
                return redirect('user_profile_update')

        elif 'update_address' in request.POST:
            address_form = UserAddressForm(request.POST)
            address_form.initial['user'] = user  # for form clean()
            address_form.instance.user = user    # for save()

            if address_form.is_valid():
                address_form.save()
                messages.success(request, "Address saved.")
                return redirect('user_profile_update')
            else:
                # Show all errors as toast messages
                for field, error_list in address_form.errors.items():
                    for error in error_list:
                        messages.error(request, error)

        elif 'update_password' in request.POST:
            password_form = UserPasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Password updated successfully.")
                return redirect('user_profile_update')
            else:
                for field, error_list in password_form.errors.items():
                    for error in error_list:
                        messages.error(request, f"{password_form.fields[field].label}: {error}")


    return render(request, 'user/profile_edit.html', {
        'user_form': user_form,
        'address_form': address_form,
        'password_form':password_form,
    })

@never_cache
@login_required(login_url='login')
def user_edit_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    if request.method == 'POST':
        form = UserAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
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

# WISHLIST MANAGEMENT FOR AUTHENTICATED USER ADDING AND REMOVING PRODUCTS, ADDING TO CART

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
    
    print('wishlist:',wishlist_items)
    return render(request, 'user/wishlist_page.html', {'wishlist_items': wishlist_items})

@never_cache
@login_required(login_url='login') 
def remove_from_wishlist(request):
    variant_id = request.POST.get('variant_id')
    variant = get_object_or_404(ProductVariant, id=variant_id)

    WishlistProducts.objects.filter(user=request.user, variant=variant).delete()
    messages.success(request, f"{variant} removed from your wishlist.")

    return redirect('user_wishlist_page')



# USER CART MANAGEMENT , ADDING PRODUCTS FOR AUTHENTICATED USERS
@never_cache
@login_required(login_url='login')
def add_to_cart(request, variant_id):
    """Add a product variant to the user's cart or update quantity if it already exists."""
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
        
        if variant.stock < 1:
            messages.error(request, f"{variant} is out of stock.")
            return redirect(request.META.get('HTTP_REFERER', 'user_cart_page'))

        if CartProducts.objects.filter(user=request.user, variant=variant).exists():
            messages.info(request,f'The item {variant} is already in the cart.')
            print(f'{variant} is already in cartl.')
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
    
    cart_item_details = []
    for item in cart_items:
        if item.quantity > item.variant.stock:
            messages.error(request, f"Insufficient stock for {item.variant}. Only {item.variant.stock} available.")
            return redirect('user_cart_page')
        original_item_price = item.quantity * item.variant.original_price
        original_total_price += original_item_price
        selling_item_price = item.quantity * item.variant.price
        selling_total_price += selling_item_price
        discount_total += original_item_price - selling_item_price
        # Store per-item calculations as strings
        cart_item_details.append({
            'variant_id': item.variant.id,
            'quantity': item.quantity,
            'item_total': str(selling_item_price),
            'item_discount': str(original_item_price - selling_item_price)
        })
    
    taxes =  Decimal('0.00')
    amount_payable = selling_total_price + taxes
    
    # Store price details in session
    request.session['cart_price_data'] = {
        'original_total_price': str(original_total_price),
        'selling_total_price': str(selling_total_price),
        'discount_total': str(discount_total),
        'taxes': str(taxes),
        'amount_payable': str(amount_payable),
        'cart_item_details': cart_item_details
    }
    
    context = {
        'cart_items': cart_items,
        'payable_amount': amount_payable,
        'original_total_price': original_total_price,
        'discount_total': discount_total,
        'selling_total_price': selling_total_price,
        'taxes': taxes,
        'estimated_delivery_date': (datetime.now() + timedelta(days=7)).strftime('%B %d, %Y'),
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
            if cart_item.quantity + 1 >= cart_item.variant.stock:messages.error(request, f"Cannot increase quantity. Stock limit reached.")
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




# USER WALLET PAGE
def users_wallet_page(request):

    return render(request,'user/wallet_page.html')