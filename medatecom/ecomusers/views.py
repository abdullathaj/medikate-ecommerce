from django.shortcuts import render,redirect,get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import UserAddress,User,WishlistProducts,CartProducts
from ecomproducts.models import Product,ProductVariant,ProductImage,Categories
from django.core.paginator import Paginator
from django.db.models import Min,Q,F,Sum,FloatField
from .forms import UserProfileForm,UserAddressForm
from django.contrib import messages
from datetime import timedelta,datetime
from decimal import Decimal

# Create your views here.
# home page for User BEFORE LOGIN

def userhomeview(request):
     # Fetch active products with related category and filter active variants
    products = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).select_related('category').order_by('-created_at').distinct()[:8]
    print(products)

    trending_products=products[:8]

    # Set up pagination (4 products per page)
    paginator = Paginator(products, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    return render(request, 'auth/home.html',{'products': page_obj})


# @login_required(login_url='login') # REDIRECT TO LOGIN PAGE FOR UNAUTHENTICATED USERS.
# @never_cache
def home_after_login(request):

    products = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).select_related('category').order_by('-created_at').distinct()[:8]
    print(products)

   

    # Set up pagination (4 products per page)
    paginator = Paginator(products, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
   

    return render(request,'auth/home.html',{'products':page_obj})

# PRODUCT DETAILING PAGE
def product_details(request, product_id):
    # Fetch the product
    product = get_object_or_404(Product, id=product_id, category__is_active=True)

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
    ).select_related('product', 'product__category').prefetch_related('product__product_image')

    # Get all active categories for filter options
    categories = Categories.objects.filter(is_active=True)

    # Get distinct brands for filter options
    brands = Product.objects.filter(
        product_variant__is_active=True,
        category__is_active=True
    ).exclude(brand__isnull=True).values_list('brand', flat=True).distinct()

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
    }

    return render(request, 'user/product_listing.html', context)



# USER PROFILE DETAILS, ADDRESS MANAGEMENT ADD EDIT AND DELETE

# @login_required(login_url='login') 
def users_profile_page(request):
    if not request.user.is_active:
        return redirect('login')
   
    return render(request,'user/profile_page.html')

# @login_required(login_url='login') 
def user_delete_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('user_profile_page')

# @login_required(login_url='login') 
def users_profile_update_page(request):
    user = request.user
    user_form = UserProfileForm(instance=user)
    address_form = UserAddressForm(initial={'user': user})

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

    return render(request, 'user/profile_edit.html', {
        'user_form': user_form,
        'address_form': address_form,
    })



# WISHLIST MANAGEMENT FOR AUTHENTICATED USER ADDING AND REMOVING PRODUCTS, ADDING TO CART

# @login_required(login_url='login') 
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

# @login_required(login_url='login') 
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

def remove_from_wishlist(request):
    variant_id = request.POST.get('variant_id')
    variant = get_object_or_404(ProductVariant, id=variant_id)

    WishlistProducts.objects.filter(user=request.user, variant=variant).delete()
    messages.success(request, f"{variant} removed from your wishlist.")

    return redirect('user_wishlist_page')



# USER CART MANAGEMENT , ADDING PRODUCTS FOR AUTHENTICATED USERS

#@login_required(login_url='login')
def add_to_cart(request, variant_id):
    """Add a product variant to the user's cart or update quantity if it already exists."""
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)

    if variant.stock < 1:
        messages.error(request, f"{variant} is out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'user_cart_page'))

    # Fetch the cart item if it exists
    cart_item = CartProducts.objects.filter(user=request.user, variant=variant).first()

    if cart_item:
        if cart_item.variant.stock < 1:
            messages.error(request, 'Stock limit reached.')
        else:
            cart_item.quantity += 1
            cart_item.variant.stock -= 1
            cart_item.variant.save()
            cart_item.save()
            messages.success(request, f"Updated quantity for {variant} in your cart is {cart_item.quantity}.")
    else:
        CartProducts.objects.create(user=request.user, variant=variant, quantity=1)
        variant.stock -= 1
        variant.save()
        messages.success(request, f"{variant} has been added to your cart.")

    return redirect(request.META.get('HTTP_REFERER', 'user_cart_page'))

def users_cart_page(request):
    if not request.user.is_active:
        return redirect('login')
    
    cart_items=CartProducts.objects.filter(
        user=request.user,
        variant__is_active=True,
        
    ).select_related('variant__product')
    print('Cart items: ',cart_items)
# PRICE CALCULATION INCLUDING SELLING PRICE, ORIGINAL PRICE,DISCOUNT PRICE, TAXES

    original_total_price=Decimal('0')
    selling_total_price=Decimal('0')
    discount_total=Decimal('0')

    for item in cart_items:
        original_item_price= item.quantity* item.variant.original_price
        original_total_price += original_item_price
        selling_item_price= item.variant.price * item.quantity
        selling_total_price += selling_item_price
        discount_total += original_item_price - selling_item_price
    taxes= selling_total_price * Decimal('0.05')
    amount_payable= selling_total_price + taxes

# TAKING USER ADDRESSES FOR DELIVERY
    addresses=UserAddress.objects.filter(user=request.user)
    default_address=UserAddress.objects.filter(is_default=True).first()
    selected_address_id=request.session.get('selected_address_id')

    if not selected_address_id or default_address:
        selected_address_id = default_address.id
        request.session['selected_address_id']= selected_address_id


    
# DELIVERY TIME
    estimated_delivery_date=(datetime.now() + timedelta(days=7)).strftime('%B %d, %Y')

    context = {
        'cart_items': cart_items,
        'payable_amount': amount_payable,
        'original_total_price': original_total_price,
        'discount_total': discount_total,
        'selling_total_price': selling_total_price,
        'taxes': taxes,
        'default_addresses': default_address,
        'selected_address_id':selected_address_id,
        'user_addresses':addresses.exclude(id=default_address.id) if default_address else addresses,
        'estimated_delivery_date': estimated_delivery_date,

    }

    return render(request,'user/cart_page.html',context)

@login_required(login_url='login')
def update_cart_quantity(request, cart_item_id):
    """Increase or decrease cart item quantity and adjust variant stock."""
    cart_item = get_object_or_404(CartProducts, user=request.user, id=cart_item_id)

    action = request.POST.get('action')
    if action == 'increase':
        if cart_item.variant.stock < 1:
            messages.error(request, 'Stock limit reached.')
        else:
            cart_item.quantity += 1
            cart_item.variant.stock -= 1
            cart_item.variant.save()
            cart_item.save()
            messages.success(request, f"Quantity updated for {cart_item.variant}.")
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.variant.stock += 1
        cart_item.variant.save()
        cart_item.save()
        messages.success(request, f"Quantity updated for {cart_item.variant}.")
    
    return redirect('user_cart_page')


def remove_cart_item(request,cart_item_id):
    """ REMOVING AN ITEM FROM THE CART """

    cart_item=get_object_or_404(CartProducts,user=request.user,id=cart_item_id)
    cart_item.variant.stock += cart_item.quantity
    cart_item.variant.save()
    cart_item.delete()

    messages.success(request, f"{cart_item.variant} removed from your cart.")

    return redirect('user_cart_page')

def save_for_later(request,cart_item_id):

    cart_item=get_object_or_404(CartProducts,user=request.user, id=cart_item_id)
    variant=cart_item.variant

    if WishlistProducts.objects.filter(user=request.user,variant=variant).exists():
        messages.error(request,f'{variant} is already in the wishlist')
    else:
        WishlistProducts.objects.create(user=request.user,variant=variant)
        messages.success(request,f'{variant} is added to the wishlist.')
    variant.stock += cart_item.quantity
    variant.save()
    cart_item.delete()
    
    return redirect('user_cart_page')

def cart_select_address(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            address_id = int(request.POST.get('selected_address'))
            address = get_object_or_404(UserAddress, id=address_id, user=request.user)

            # Save to session (don't change default status)
            request.session['selected_address_id'] = address.id
            messages.success(request, "Delivery address selected successfully.")
        except (TypeError, ValueError):
            messages.error(request, "Invalid address selection.")
    else:
        messages.error(request, "Invalid request.")

    return redirect('user_cart_page')







# @login_required(login_url='login') 
def buy_now(request,variant_id):
    pass

# USER ORDERS PAGE
def users_orders_page(request):

    return render(request,'user/orders_page.html')


# USER WALLET PAGE
def users_wallet_page(request):

    return render(request,'user/wallet_page.html')