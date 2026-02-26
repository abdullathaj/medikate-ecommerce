from django.shortcuts import render,redirect,get_object_or_404
from ecomusers.models import User,Wallet,WalletTransaction,Referral,ContactMessage
from ecomproducts.models import Categories,Product,ProductVariant,ProductImage,Coupon,Offer
from ecomorders.models import Order,OrderItem,ReturnRequest
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from .forms import Useraddform,CategoryAddForm,ProductAddForm,ProductImageForm,VariantAddForm,VariantFormset,ImageFormset
from .forms import CouponForm,OfferForm,CouponEditForm,OfferEditForm
from django.db import transaction
from django.contrib import messages
from django.forms import inlineformset_factory
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q,Sum, Count, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from ecomorders.utils import render_to_pdf
from django.http import HttpResponse
from datetime import datetime
import json




# Create your views here.

# DASHBOARD for Admin


@staff_member_required
@never_cache
def admin_dashboard(request):
    ''' DASHBOARD OF ADMIN PAGE WHICH CONTAINS THE LINK FOR OTHER PAGES AND IT IS MIGRATING TO ALL THE PAGES.'''
    customers= User.objects.all()
    customer_count= customers.count()
    active_users= customers.filter(is_active= True).count()
    inactive_users= customers.filter(is_active= False).count()

    categories= Categories.objects.all()
    category_count= categories.count()
    active_categories= categories.filter(is_active= True).count()
    inactive_categories= categories.filter(is_active= False).count()

    products= ProductVariant.objects.all()
    product_count= products.count()
    active_products= products.filter(is_active= True).count()
    inactive_products= products.filter(is_active= False).count()

    coupons= Coupon.objects.all()
    coupon_count= coupons.count()
    valid_coupons= len([i for i in coupons if i.is_valid])
    invalid_coupons= coupon_count-valid_coupons
    active_coupons= coupons.filter(is_active=True).count()
    inactive_coupons= coupon_count-active_coupons


    offers= Offer.objects.all()
    offer_count= offers.count()
    active_offers= offers.filter(is_active= True).count()
    inactive_offers= offers.filter(is_active= False).count()
    valid_offers= len([i for i in offers if i.is_valid])
    invalid_offers= len([i for i in offers if not i.is_valid])
    
    orders= Order.objects.all()
    order_count= orders.count()
    cod_count= orders.filter(payment_method='COD').count()
    wallet_count= orders.filter(payment_method='WALLET').count()
    online_count= orders.filter(payment_method='RAZORPAY').count()

    referrals= Referral.objects.all()
    referral_count= referrals.count()
    referrer_count= referrals.values('referrer').distinct().count()

    breadcrumbs=[
        {'name':'Dashboard','url': ''},
        ]
    context= {
        'breadcrumbs':breadcrumbs, 
        'customer_count':customer_count, 'active_users':active_users, 'inactive_users':inactive_users,
        'category_count':category_count, 'active_categories':active_categories, 'inactive_categories':inactive_categories,
        'product_count':product_count, 'active_products':active_products, 'inactive_products':inactive_products,
        'coupon_count':coupon_count, 'valid_coupons':valid_coupons, 'invalid_coupons':invalid_coupons,'active_coupons':active_coupons,'inactive_coupons':inactive_coupons,
        'offer_count':offer_count, 'active_offers':active_offers, 'inactive_offers':inactive_offers,'valid_offers':valid_offers,'invalid_offers':invalid_offers,
        'order_count':order_count, 'cod_count':cod_count, 'wallet_count':wallet_count, 'online_count':online_count,
        'referral_count':referral_count, 'referrer_count':referrer_count
        }
    return render(request,'admin/dashboard_admin.html',context)

def dashboard_sales_chart(request):

    filter_type = request.GET.get('filter', 'yearly')
    now = timezone.now()

    # 1. Date Filtering Logic
    if filter_type == 'monthly':
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
    elif filter_type == 'weekly':
        start_date = now - timedelta(days=7)
    else:  # Yearly
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)

    # Base queryset for active/delivered sales
    sold_items = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        status='ACTIVE', # Adjust based on your status logic (e.g., exclude cancelled)
        order__is_paid=True
    )

    
    top_products = sold_items.values(
        'variant__product__name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(
            ExpressionWrapper(
                F('price') * F('quantity'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    ).order_by('-total_sold')[:10]
    print('top products',top_products)

   
    top_categories = sold_items.values(
        'variant__product__category__name'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:10]
    print('top categories',top_categories)

   
    top_brands = sold_items.values(
        'variant__product__brand'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:10]

    print('top brands',top_brands)

    context = {
        'filter_type': filter_type,
        'top_products': top_products,
        'top_categories': top_categories,
        'top_brands': top_brands,
    }

    return render(request,'admin/dashboard_sales_chart.html',context)
# ---------------------------------------------------------------------------------------------------
# USER MANAGEMENT FOR ADMIN                                                                          
# ---------------------------------------------------------------------------------------------------
@staff_member_required(login_url='admin_login')
@never_cache
def admin_customer_details(request):
    users = User.objects.all()
    print(users)
    query=request.GET.get('q','')
    if query:
        users=users.filter(
            Q(username__icontains=query)|
            Q(email__icontains=query)|
            Q(first_name__icontains=query)
        )
    paginator=Paginator(users,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Customer', 'url':''},
    ]

    return render(request,'admin/user_details.html',{'users':users,'page_obj':page_obj,
                                                         'query':query, 'breadcrumbs':breadcrumbs})

@staff_member_required(login_url='admin_login')
@never_cache
def admin_add_user(request):
    if request.method=='POST':
        form=Useraddform(request.POST)
        if form.is_valid():
            user = form.save()
            print(user)
            messages.success(request, f'{user.username} has been created.')
            return redirect('customer_details')
        else:
            messages.error(request,'Please add valid credentials.')
    else:
        form=Useraddform()
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Customer', 'url':'customer_details'},
        {'name': 'Add user', 'url': ''},
    ]       
    return render(request, 'admin/user_creation.html', {'form': form, 'breadcrumbs': breadcrumbs}) 

@staff_member_required(login_url='admin_login')
@never_cache
def admin_block_user(request,user_id):
    ''' ADMIN BLOCKING AND UNBLOCKING THE EXISTING USERS.'''

    user=get_object_or_404(User,id=user_id)
    if request.method=='POST' and not user.is_superuser:
        user.is_active=not user.is_active
        user.save()
        status='unblocked' if user.is_active else 'blocked'
        messages.success(request,f'User {user.username} has been {status}...')
    return redirect('customer_details')


# -----------------------------------------------------------------------------------------------------------
# ADMIN CATEGORY MANAGEMENT
# -------------------------------------------------------------------------------------------------------------

@staff_member_required(login_url='admin_login')
# @never_cache
def admin_category_list(request):
    categories=Categories.objects.all()
    query=request.GET.get('q','')
    if query:
        categories=categories.filter(
            Q(name__icontains=query)|
            Q(description__icontains=query)
        )

    paginator=Paginator(categories,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Categories', 'url':''},
    ]

    return render(request,'admin/category_list.html',{'page_obj':page_obj,'query':query, 'breadcrumbs': breadcrumbs})


@staff_member_required(login_url='admin_login')
@never_cache
def admin_add_category(request):

    if request.method == 'POST':
        form = CategoryAddForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('admin_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryAddForm()
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Categories', 'url':'admin_categories'},
        {'name': 'Add category', 'url': ''}
    ]
    return render(request,'admin/category_add.html',{'form':form, 'breadcrumbs':breadcrumbs})


@staff_member_required(login_url='admin_login')
@never_cache
def admin_hide_category(request, category_id):
    ''' ADMIN HIDES AND UNHIDES THE EXISTING CATEGORIES.'''

    category = get_object_or_404(Categories, id=category_id)

    if request.method == "POST":
        category.is_active = not category.is_active
        category.save()
        messages.success(request, f"Category '{category.name}' is now {'visible' if category.is_active else 'hidden'}.")

    return redirect('admin_categories')


@staff_member_required(login_url='admin_login')
@never_cache
def admin_edit_category(request, category_id):
    ''' ADMIN CAN EDIT THE EXISTING CATEGORY DETAILS.'''
    category = get_object_or_404(Categories, id=category_id)

    if request.method == 'POST':
        form = CategoryAddForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('admin_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryAddForm(instance=category)
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Categories', 'url':'admin_categories'},
        {'name': 'Edit category', 'url': ''}
    ]
    return render(request, 'admin/edit_category.html', {'form': form, 'category': category, 'breadcrumbs':breadcrumbs})
    
###############################################################################################################################

# --------------------------------------------------------------------------------------------------------
# ADMIN PRODUCT MANAGEMENT
# ----------------------------------------------------------------------------------------------------------

# PRODUCT TABLE
@staff_member_required(login_url='admin_login')
# @never_cache
def admin_product_details(request):
    products=Product.objects.all().order_by('id')
    variants=ProductVariant.objects.select_related('product__category').order_by('product__id')
    categories=Categories.objects.all()

    # filter by categories
    category_id=request.GET.get('category')
    if category_id and category_id.isdigit():
        variants=variants.filter(product__category_id=category_id)

    # order by created at
    sort=request.GET.get('sort','newest')
    if sort=='newest':
        variants=variants.order_by('-product__created_at')
    elif sort=='oldest':
        variants=variants.order_by('product__created_at')
    
    query = request.GET.get('q')
    if query:
        variants = variants.filter(
            Q(product__name__icontains=query) |
            Q(variant_name__icontains=query) |
            Q(product__category__name__icontains=query)
        )
    paginator=Paginator(variants,20)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Products', 'url':''},
    ]
    return render(request,'admin/product_list.html',
                  {'products':products,
                   'variants':page_obj,'page_obj':page_obj,
                   'query':query,'categories':categories,
                   'sort':sort,'selected_category':category_id,
                   'breadcrumbs': breadcrumbs})


@staff_member_required(login_url='admin_login')
@never_cache
def admin_add_product(request):
    ''' ADMIN CAN ADD NEW PRODUCT IN THE EXISTING CATEGORIES. ADDING NAME, IMAGE, DESCRIPTION, STOCK, VARIANT NAME,
        PRICE, SIZE, ETC.'''

    variant_formset = VariantFormset
    image_formset = ImageFormset

    form_errors = []  

    if request.method == 'POST':
        product_form = ProductAddForm(request.POST)
        variant_form = variant_formset(request.POST, prefix='variants')
        image_form = image_formset(request.POST, request.FILES, prefix='images')

        if product_form.is_valid() and variant_form.is_valid() and image_form.is_valid():
            try:
                product = product_form.save()
                variants = variant_form.save(commit=False)
                if not variants:
                    raise ValidationError('At least one Variant is required.')
                for variant in variants:
                    variant.product = product
                    variant.save()
                images = image_form.save(commit=False)
                if len([img for img in images if img.image]) != 3:
                    raise ValidationError("Exactly 3 images needed.")
                for image in images:
                    if image.image:
                        image.product = product
                        image.save()
                messages.success(request, 'Product, Variant are created and uploaded 3 Images.')
                return redirect('admin_product_list')
            except ValidationError as e:
                form_errors = e.messages
                for err in form_errors:
                    messages.error(request, err)
        else:
            form_errors.extend(product_form.non_field_errors())
            form_errors.extend(variant_form.non_form_errors())
            form_errors.extend(image_form.non_form_errors())

            for form in variant_form:
                form_errors.extend(form.non_field_errors())
                for field, errors in form.errors.items():
                    form_errors.extend(errors)

            for form in image_form:
                form_errors.extend(form.non_field_errors())
                for field, errors in form.errors.items():
                    form_errors.extend(errors)

            for err in form_errors:
                messages.error(request, err)
    else:
        product_form = ProductAddForm()
        variant_form = variant_formset(prefix='variants')
        image_form = image_formset(prefix='images')

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Products', 'url':'admin_product_list'},
        {'name': 'Add product', 'url': ''}
    ]
    return render(request, 'admin/product_add.html', {
        'product_form': product_form,
        'variant_form': variant_form,
        'image_form': image_form,
        'form_errors': form_errors,
        'breadcrumbs': breadcrumbs 
    })


@staff_member_required(login_url='admin_login')
@never_cache
def admin_edit_product(request,product_id):
    ''' ADMIN EDITS PRODUCT NAME, CATEGORY, IMAGES AND OTHER PRODUCT DETAILS.'''
    
    product = get_object_or_404(Product, id=product_id)
    variant_formset = VariantFormset
    image_formset = ImageFormset
    form_errors = []
    if request.method == 'POST':
        product_form = ProductAddForm(request.POST, instance=product)
        variant_form = variant_formset(request.POST, instance=product, prefix='variants')
        image_form = image_formset(request.POST, request.FILES, instance=product, prefix='images')
        try:
            if product_form.is_valid() and variant_form.is_valid() and image_form.is_valid():
                product = product_form.save()
                variants = variant_form.save(commit=False)
                # if not variants:
                #     raise ValidationError('At least one variant is required.')
                for variant in variants:
                    variant.product = product
                    variant.save()
                
                images = image_form.save(commit=False)
            
                for image in images:
                    image.product = product
                    image.save()
        
                total_images = ProductImage.objects.filter(product=product).count()
                if total_images != 3:
                    raise ValidationError(f"Exactly 3 images are required. Currently, there are {total_images} images.")
                
                
                messages.success(request, f"Product '{product.name}' updated successfully.")
                return redirect('admin_product_list')
            else:
                form_errors = []
                form_errors.extend(product_form.non_field_errors())
                form_errors.extend(variant_form.non_form_errors())
                form_errors.extend(image_form.non_form_errors())

                for form in variant_form:
                    form_errors.extend(form.non_field_errors())
                    for field, errors in form.errors.items():
                        form_errors.extend(errors)

                for form in image_form:
                    form_errors.extend(form.non_field_errors())
                    for field, errors in form.errors.items():
                        form_errors.extend(errors)

                print('Form Errors:',form_errors)
        except ValidationError as e:
            form_errors = e.messages
            for msg in form_errors:
                messages.error(request,msg)
            print('Validation Errors:',form_errors)
    else:
        product_form = ProductAddForm(instance=product)
        variant_form = variant_formset(instance=product, prefix='variants')
        image_form = image_formset(instance=product, prefix='images')

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Products', 'url':'admin_product_list'},
        {'name': 'Edit product', 'url': ''}
    ]
    return render(request, 'admin/product_edit.html', {
        'product_form': product_form,
        'variant_form': variant_form,
        'image_form': image_form,
        'form_errors': form_errors,
        'product': product,
        'breadcrumbs': breadcrumbs
    })


@staff_member_required(login_url='admin_login')
@never_cache
def admin_hide_product(request, variant_id):
    ''' HIDE AND SHOWING THE PRODUCTS VARIANTS IF NEEDED. '''

    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.method == "POST":
        variant.is_active = not variant.is_active
        variant.save()
        messages.success(request, f"Product '{variant.product.name}' is now {'visible' if variant.is_active else 'hidden'}.")

    return redirect('admin_product_list')

#################################################################################################################################

# ---------------------------------------------------------------------------------------------
# ADMIN ORDER MANAGEMENT
# ----------------------------------------------------------------------------------------------

@staff_member_required(login_url='admin_login')
def admin_order_list(request):
    
    ''' TABLE LISTING OF ORDERS'''
    query = request.GET.get('q', '').strip()
    orders = Order.objects.all().order_by('-created_at')  
    order_count=Order.objects.count()

    if query:
        orders = orders.filter(
            Q(id__icontains=query) |
            Q(user__email__icontains=query) |
            Q(address__addressline_1__icontains=query) |
            Q(address__addressline_2__icontains=query) |
            Q(address__city__icontains=query) |
            Q(address__state__icontains=query) |
            Q(address__nation__icontains=query) |
            Q(address__postal_code__icontains=query) |
            Q(items__variant__product__name__icontains=query) |
            Q(items__variant__product__category__name__icontains=query)
        ).distinct()

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Orders', 'url':''},
    ]
    context = {
        'query': query,
        'orders': page_obj,
        'order_count':order_count,
        'breadcrumbs': breadcrumbs
    }
    return render(request, 'admin/order_list.html', context)

@staff_member_required(login_url='admin_login')
def admin_order_item_list(request, order_id):
    
    ''' TABLE LISTING OF ORDER ITEMS.'''

    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Orders', 'url':'admin_order_list'},
        {'name': 'Order Item', 'url': ''}
    ]
    context = {'order': order, 'items': items, 'breadcrumbs': breadcrumbs}
    return render(request, 'admin/order_item_list.html', context)

@staff_member_required(login_url='admin_login')
@never_cache
def admin_edit_order_status(request, item_id):
    
    ''' ADMIN CAN EDIT ORDER STATUS- DELIVERED, SHIPPED, ETC..'''

    if request.method == 'POST':
        item = get_object_or_404(OrderItem, id=item_id)
        new_status = request.POST.get('delivery_status')
        
        # Validate the new status
        valid_statuses = [status for status, _ in OrderItem.DELIVERY_STATUS_CHOICES if status not in ('CANCELLED','RETURNED') ]
        if new_status in valid_statuses:
            item.delivery_status = new_status
            item.save()
            messages.success(request, f"Delivery status for Order Item #{item.id} updated to {new_status}.")
        else:
            messages.error(request, "Invalid delivery status selected.")
        
        return redirect('admin_order_item_list', order_id=item.order.id)
    
    # If not POST, redirect to the order items list
    item = get_object_or_404(OrderItem, id=item_id)
    return redirect('admin/admin_order_item_list', order_id=item.order.id)

@staff_member_required(login_url='admin_login')
def admin_request_list(request):
    
    ''' LIST OF REOUESTS FOR ADMIN APPROVAL FOR RETUTN ORDERS. '''

    return_requests= ReturnRequest.objects.all().select_related('order_item__order','order_item__variant').order_by('-created_at')
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Requests', 'url':''},
    ]
    context= {'return_requests':return_requests, 'breadcrumbs': breadcrumbs}
    return render(request,'admin/return_request_list.html',context)

@never_cache
@staff_member_required(login_url='admin_login')
def admin_return_approval(request, request_id):
    """ ADMIN CAN APPROVE OR DENY THE RETURN REQUESTS. """
    return_request = get_object_or_404(ReturnRequest, id=request_id)
    item = return_request.order_item  
    order = item.order

    if return_request.status != 'PENDING':
        messages.warning(request, 'This return request is already processed.')
        return redirect('admin_request_list')

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            with transaction.atomic():
                if action == 'APPROVE':
                    return_request.status = 'APPROVED'
                    return_request.save()

                    item.status = 'RETURNED'
                    item.delivery_status = 'RETURNED'
                    item.return_reason = return_request.reason
                    item.return_other_reason = return_request.other_reason
                    item.save()

                    item.variant.stock += item.quantity
                    item.variant.save()

                    original_subtotal = sum(it.price * it.quantity for it in order.items.all())
                    
                    item_refund_basis = item.quantity * item.price

                    if original_subtotal > 0:
                        refund_amount = item_refund_basis
                    else:
                        refund_amount = 0
                    
                    refund_amount = Decimal(refund_amount).quantize(Decimal("0.01"))

                    order.total_amount = max(0, order.total_amount - refund_amount)
                    order.save()

                    wallet, _ = Wallet.objects.get_or_create(user=order.user)
                    wallet.balance += refund_amount
                    wallet.save()

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='CREDIT',
                        amount=refund_amount,
                        description=f'Return Refund for Order Return',
                        transaction_source='RETURN',
                        order=order,
                        order_item=item
                    )
                    messages.success(request, f'Approved. ₹{refund_amount} refunded to wallet.')

                elif action == 'DENY':
                    return_request.status = 'DENIED'
                    return_request.save()
  
                    item.status = 'ACTIVE' 
                    item.delivery_status = 'DELIVERED'
                    item.save()
                    messages.warning(request, f'Return request denied.')

                return redirect('admin_request_list')
        except Exception as e:
            print(f'Exception occured as {e}')
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_request_list')

    return render(request, 'admin/return_approval.html', {'return_request': return_request, 'item': item, 'order': order})

#################################################################################################################################

# ----------------------------------------------------------------------------------------------
# ADMIN COUPON MANAGEMENT
# ---------------------------------------------------------------------------------------------

@staff_member_required(login_url='admin_login')
def admin_coupon_list(request):

    coupons = Coupon.objects.all().order_by('-created_at')
    
    query = request.GET.get('q', '')
    if query:
        coupons = coupons.filter(
            Q(coupon_code__icontains=query) |
            Q(description__icontains=query)
        )
    
    paginator = Paginator(coupons, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Coupons', 'url':''},
    ]
    context = {
        'coupons': page_obj,
        'coupon_count': paginator.count,
        'query': query,
        'breadcrumbs': breadcrumbs
    }
    
    return render(request, 'admin/coupon_list.html', context)

@never_cache
@staff_member_required(login_url='admin_login')
def admin_coupon_creation(request):
    
    ''' ADMIN CAN CREATE COUPON WITH THE FIELDS OF 
    COUPON CODE, PERCENTAGE, DESCRIPTION, VALIDITY, PURCHASE AMOUNT AND USAGE LIMIT.'''

    if request.method == 'POST':
        form= CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'Coupon created successfully.')
            return redirect('admin_coupon_list')
        else:
            messages.warning(request,'Please fill the form correctly.')
    else:
        form= CouponForm()
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Coupons', 'url':'admin_coupon_list'},
        {'name': 'Create Coupon', 'url': ''}
    ]
    return render(request,'admin/coupon_creation.html',{'form': form, 'breadcrumbs': breadcrumbs})

@never_cache
@staff_member_required(login_url='admin_login')
def admin_coupon_delete(request, coupon_id):
    
    ''' ADMIN CAN DELETE A COUPON IF IT IS NOT NEED LONGER.'''

    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, f"Coupon '{coupon.coupon_code}' deleted successfully.")
        return redirect('admin_coupon_list')
    
    messages.warning(request, "Invalid request method.")
    return redirect('admin_coupon_list')

@never_cache
@staff_member_required
def admin_coupon_edit(request,coupon_id):
    coupon= get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        form= CouponEditForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request,'Coupon modified successfully.')
            return redirect('admin_coupon_list')
        else:
            messages.warning(request,'Please fill the form correctly.')
    else:
        form= CouponEditForm(instance=coupon)
    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Coupons', 'url':'admin_coupon_list'},
        {'name': 'Edit Coupon', 'url': ''}
    ]
    return render(request,'admin/coupon_edit.html',{'form':form,'coupon':coupon ,'breadcrumbs':breadcrumbs})
#################################################################################################################################

# --------------------------------------------------------------------------------
# ADMIN OFFER MANAGEMENT
# ----------------------------------------------------------------------------------

@staff_member_required(login_url='admin_login')
def admin_offer_list(request):
    """Display all product and category offers with pagination and search."""
    offers = Offer.objects.select_related('product', 'category').order_by('-created_at')

    query = request.GET.get('q', '')
    if query:
        offers = offers.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(product__name__icontains=query) |
            Q(category__name__icontains=query)
        )

    paginator = Paginator(offers, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Offers', 'url':''},
    ]
    context = {
        'offers': page_obj,
        'offer_count': paginator.count,
        'query': query,
        'breadcrumbs': breadcrumbs
    }

    return render(request, 'admin/offer_list.html', context)

@never_cache
@staff_member_required(login_url='admin_login')
def admin_offer_creation(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Offer created successfully!')
            return redirect('admin_offer_list')
        else:
            messages.error(request, 'Please fill the fields carefully.')
    else:
        form = OfferForm()

    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Offers', 'url':'admin_offer_list'},
        {'name': 'Offer Creation', 'url': ''}
    ]
    return render(request, 'admin/offer_creation.html', {'form': form, 'breadcrumbs': breadcrumbs})

@never_cache
@staff_member_required(login_url='admin_login')
def admin_offer_delete(request,offer_id):
    offer= get_object_or_404(Offer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request,f'Offer {offer.name} deleted successfully.')
        return redirect('admin_offer_list')
    messages.error(request,'Invalid request method.')
    return redirect('admin_offer_list')

@never_cache
@staff_member_required(login_url='admin_login')
def admin_offer_edit(request,offer_id):
    offer= get_object_or_404(Offer,id=offer_id)
    if request.method == 'POST':
        form= OfferEditForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request,'Offer modified successfully.')
            return redirect('admin_offer_list')
        else:
            messages.error(request,'Please fill the fields carefully.')
    else:
        form= OfferEditForm(instance=offer)

    breadcrumbs=[
        {'name':'Dashboard', 'url':'admin_dashboard'},
        {'name':'Offers', 'url':'admin_offer_list'},
        {'name':'Offer edit', 'url':''}
    ]
    return render(request,'admin/offer_edit.html',{'breadcrumbs':breadcrumbs,'offer':offer, 'form':form})

# ---------------------------------------------------------------------------------------
# SALES REPORT OF THE WEBSITE
# -----------------------------------------------------------------------------------------
@staff_member_required(login_url='admin_login')
def admin_sales_report(request):
    
    
    period = request.GET.get('period', 'overall')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.all().order_by('-created_at')
    
    if period == 'daily':
        orders = orders.filter(created_at__date=timezone.now().date())
    elif period == 'weekly':
        start_week = timezone.now() - timedelta(days=timezone.now().weekday())
        orders = orders.filter(created_at__gte=start_week)
    elif period == 'monthly':
        orders = orders.filter(created_at__month=timezone.now().month, created_at__year=timezone.now().year)
    elif period == 'yearly':
        orders = orders.filter(created_at__year=timezone.now().year)
    elif period == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    
    total_order = orders.count()
    valid_orders = orders.exclude(
        items__delivery_status__in=['CANCELLED', 'RETURNED']
    ).distinct()

    total_revenue = (
        valid_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    )
    total_offer_discount = (
        valid_orders.aggregate(total=Sum('offer_discount'))['total'] or 0
        )

    total_coupon_discount = (
        valid_orders.aggregate(total=Sum('coupon_discount'))['total'] or 0
        )
    
    items = OrderItem.objects.filter(order__in=orders)
    total_items = items.aggregate(total=Sum('quantity'))['total'] or 0
    
    
    pendings = items.filter(delivery_status='PENDING').count()
    deliveries = items.filter(delivery_status='DELIVERED').count()
    cancelled = items.filter(delivery_status='CANCELLED').count()
    returns = items.filter(delivery_status='RETURNED').count()

    
    avg_order_value = round(total_revenue / total_order, 2) if total_order > 0 else 0
    
    top_payment_method = orders.values('payment_method').annotate(count=Count('payment_method')).order_by('-count').first()
    top_customer = orders.values('user__username').annotate(count=Count('id')).order_by('-count').first()
    
    
    top_product = items.values('variant__product__name').annotate(count=Count('id')).order_by('-count').first()
    top_category = items.values('variant__product__category__name').annotate(count=Count('id')).order_by('-count').first()


    breadcrumbs=[
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Sales report', 'url':''},
    ]
    
    context = {
        'breadcrumbs': breadcrumbs,
        'total_order': total_order,
        'total_items': total_items,
        'total_revenue': total_revenue,
        'average_order_value': avg_order_value,
        'total_offer_discount': total_offer_discount,
        'total_coupon_discount': total_coupon_discount,
        'pendings': pendings, 
        'deliveries': deliveries,
        'cancelled': cancelled, 
        'returns': returns,
        'top_payment_method': top_payment_method,
        'top_customer': top_customer,
        'top_product': top_product,
        'top_category': top_category,
        'current_period': period,
        'start_date': start_date,
        'end_date': end_date
    }

    return render(request, 'admin/sales_report.html', context)

@staff_member_required(login_url='admin_login')
def admin_sales_report_pdf(request):
    
    period = request.GET.get('period', 'overall')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    orders = Order.objects.all().order_by('-created_at')

    if period == 'daily':
        orders = orders.filter(created_at__date=timezone.now().date())
    elif period == 'weekly':
        start_week = timezone.now() - timedelta(days=timezone.now().weekday())
        orders = orders.filter(created_at__gte=start_week)
    elif period == 'monthly':
        orders = orders.filter(created_at__month=timezone.now().month, created_at__year=timezone.now().year)
    elif period == 'yearly':
        orders = orders.filter(created_at__year=timezone.now().year)
    elif period == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])

    total_order = orders.count()
    valid_orders = orders.exclude(
        items__delivery_status__in=['CANCELLED', 'RETURNED']
    ).distinct() 

    total_revenue = (
        valid_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    )

    total_offer_discount = (
        valid_orders.aggregate(total=Sum('offer_discount'))['total'] or 0
    )

    total_coupon_discount = (
        valid_orders.aggregate(total=Sum('coupon_discount'))['total'] or 0
    )
    items = OrderItem.objects.filter(order__in=orders)
    total_items = items.count()

    pendings = items.filter(delivery_status='PENDING').count()
    deliveries = items.filter(delivery_status='DELIVERED').count()
    cancelled = items.filter(delivery_status='CANCELLED').count()
    returns = items.filter(delivery_status='RETURNED').count()
    
    avg_order_value = round(total_revenue / total_order, 2) if total_order > 0 else 0
    
    top_payment_method = orders.values('payment_method').annotate(count=Count('payment_method')).order_by('-count').first()
    top_customer = orders.values('user__username').annotate(count=Count('id')).order_by('-count').first()
    top_product = items.values('variant__product__name').annotate(count=Count('id')).order_by('-count').first()
    top_category = items.values('variant__product__category__name').annotate(count=Count('id')).order_by('-count').first()

    context = {
        'total_order': total_order,
        'total_items': total_items,
        'total_revenue': total_revenue,
        'total_offer_discount': total_offer_discount,
        'total_coupon_discount': total_coupon_discount,
        'average_order_value': avg_order_value,
        'pendings': pendings, 
        'deliveries': deliveries,
        'cancelled': cancelled, 
        'returns': returns,
        'top_payment_method': top_payment_method,
        'top_customer': top_customer,
        'top_product': top_product,
        'top_category': top_category,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'generated_at': timezone.now()
    }
    
    pdf = render_to_pdf('admin/sales_report_pdf.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Sales_Report_{period}_{timezone.now().date()}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse('Error generating PDF', status=500)

@staff_member_required
def admin_wallet_transactions(request):
    transactions = WalletTransaction.objects.all().order_by('-created_at')

    paginator = Paginator(transactions,12)
    page_num = request.GET.get('page')
    page_obj = paginator.get_page(page_num)

    context={'transactions': page_obj,'transaction_count': paginator.count}
    return render(request,'admin/wallet_transactions.html',context)

@staff_member_required
def admin_wallet_details(request,transaction_id):
    wallet_transaction = get_object_or_404(WalletTransaction,id=transaction_id)
    user= wallet_transaction.wallet.user

    context={
        'wallet_transaction': wallet_transaction,
        'user': user
    }

    
    return render(request,'admin/wallet_details.html',context )


#################################################################################################################################

# ----------------------------------------------------------------------------------------------
# ADMIN CONTACT MESSAGE MANAGEMENT
# ----------------------------------------------------------------------------------------------

@staff_member_required(login_url='admin_login')
@never_cache
def admin_contact_messages(request):
    ''' LIST ALL CONTACT MESSAGES FROM USERS WITH SEARCH AND PAGINATION '''
    contact_messages = ContactMessage.objects.all().select_related('user').order_by('-created_at')

    query = request.GET.get('q', '').strip()
    if query:
        contact_messages = contact_messages.filter(
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(title__icontains=query) |
            Q(message__icontains=query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        contact_messages = contact_messages.filter(status=status_filter)

    paginator = Paginator(contact_messages, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    breadcrumbs = [
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Contact Messages', 'url': ''},
    ]

    context = {
        'contact_messages': page_obj,
        'message_count': paginator.count,
        'query': query,
        'status_filter': status_filter,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'admin/contact_messages.html', context)


@staff_member_required(login_url='admin_login')
@never_cache
def admin_contact_detail(request, message_id):
    ''' VIEW AND REPLY TO A SPECIFIC CONTACT MESSAGE '''
    contact_message = get_object_or_404(ContactMessage, id=message_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_reply = request.POST.get('admin_reply', '').strip()

        valid_statuses = [s[0] for s in ContactMessage.STATUS_CHOICES]
        if new_status in valid_statuses:
            contact_message.status = new_status
        
        if admin_reply:
            contact_message.admin_reply = admin_reply
        
        contact_message.save()
        messages.success(request, f'Message from {contact_message.user.username} updated successfully.')
        return redirect('admin_contact_detail', message_id=message_id)

    breadcrumbs = [
        {'name': 'Dashboard', 'url': 'admin_dashboard'},
        {'name': 'Contact Messages', 'url': 'admin_contact_messages'},
        {'name': 'Message Detail', 'url': ''},
    ]

    context = {
        'contact_message': contact_message,
        'status_choices': ContactMessage.STATUS_CHOICES,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'admin/contact_detail.html', context)