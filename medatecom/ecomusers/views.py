from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from ecomproducts.models import Product,ProductVariant,ProductImage,Categories
from django.core.paginator import Paginator
from django.db.models import Min,Q

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

# HOME PAGE AFTER LOGIN

@login_required(login_url='login') # REDIRECT TO LOGIN PAGE FOR UNAUTHENTICATED USERS.
@never_cache
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
# USER CART MANAGEMENT

# ADD TO CART
def add_to_cart(request,variant_id):
    pass

# BUY NOW THE PRODUCT
def buy_now(request,variant_id):
    pass

# ADD TO WISHLIST
def add_to_wishlist(request,variant_id):
    pass

def users_cart_page(request):

    return render(request,'user/cart_page.html')

# USER PROFILE MANAGEMENT
def users_profile_page(request):

    return render(request,'user/profile_page.html')

# USER ORDERS PAGE
def users_orders_page(request):

    return render(request,'user/orders_page.html')

# USER WISHLIST PAGE
def users_wishlist_page(request):

    return render(request,'user/user_wishlist.html')

# USER WALLET PAGE
def users_wallet_page(request):

    return render(request,'user/wallet_page.html')