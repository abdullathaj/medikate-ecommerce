from django.shortcuts import render,redirect,get_object_or_404
from ecomproducts.models import Product,Product_Varients,ProductImage,Categories
from django.core.paginator import Paginator

# Create your views here.
#home page for User
def userhomeview(request):
     # Fetch active products with related category and filter active variants
    products = Product.objects.filter(
        product_varient__is_active=True,
        category__is_active=True
    ).select_related('category').distinct()
    print(products)

    # Set up pagination (4 products per page)
    paginator = Paginator(products, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'auth/home.html',{'products': page_obj})

# HOME PAGE AFTER LOGIN
def home_after_login(request):
    products = Product.objects.filter(
        product_varient__is_active=True,
        category__is_active=True
    ).select_related('category').distinct()
    print(products)

    # Set up pagination (4 products per page)
    paginator = Paginator(products, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    

    return render(request,'auth/home.html',{'products':page_obj})


def product_details(request,product_id):
    product = get_object_or_404(Product, id=product_id, category__is_active=True)
    varients = product.product_varient.filter(is_active=True)

    return render(request,'user/product_details.html',{'product':product,'varients':varients})