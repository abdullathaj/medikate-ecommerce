from django.shortcuts import render,redirect,get_object_or_404
from ecomusers.models import User,Wallet
from ecomproducts.models import Categories,Product,ProductVariant,ProductImage,Coupon,Offer
from ecomorders.models import Order,OrderItem,ReturnRequest
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from .forms import Useraddform,CategoryAddForm,ProductAddForm,ProductImageForm,VariantAddForm,VariantFormset,ImageFormset
from .forms import CouponForm,OfferForm
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




# Create your views here.

# DASHBOARD for Admin

@staff_member_required
@never_cache
def admin_dashboard(request):

    
    
    return render(request,'admin/dashboard.html')


# USER MANAGEMENT FOR ADMIN
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

    return render(request,'admin/customer_details.html',{'users':users,'page_obj':page_obj,'query':query})


# ADD NEW USER
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
   return render(request, 'admin/add_user.html', {'form': form}) 



# ADMIN BLOCK AND UNBLOCK USER

@staff_member_required(login_url='admin_login')
@never_cache
def admin_block_user(request,user_id):
    user=get_object_or_404(User,id=user_id)
    if request.method=='POST' and not user.is_superuser:
        user.is_active=not user.is_active
        user.save()
        status='unblocked' if user.is_active else 'blocked'
        messages.success(request,f'User {user.username} has been {status}...')
    return redirect(admin_customer_details)

################################################################################################################################

# ADMIN CATEGORY MANAGEMENT


# CATEGORY TABLE
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

    return render(request,'admin/category_list.html',{'page_obj':page_obj,'query':query})


# ADMIN ADDING NEW CATEGORY
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

    return render(request,'admin/category_add.html',{'form':form})


# ADMIN HIDE AND SHOWING CATEGORIES
@staff_member_required(login_url='admin_login')
@never_cache
def admin_hide_category(request, category_id):
    category = get_object_or_404(Categories, id=category_id)

    if request.method == "POST":
        category.is_active = not category.is_active
        category.save()
        messages.success(request, f"Category '{category.name}' is now {'visible' if category.is_active else 'hidden'}.")

    return redirect('admin_categories')


# ADMIN EDITING CATEGORIES
@staff_member_required(login_url='admin_login')
@never_cache
def admin_edit_category(request, category_id):
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

    return render(request, 'admin/edit_category.html', {'form': form, 'category': category})
    
###############################################################################################################################

# ADMIN PRODUCT MANAGEMENT

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
    paginator=Paginator(variants,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    return render(request,'admin/product_list.html',
                  {'products':products,
                   'variants':page_obj,'page_obj':page_obj,
                   'query':query,'categories':categories,
                   'sort':sort,'selected_category':category_id})


# ADMIN ADDING NEW PRODUCT,VATIENT AND IMAGES
@staff_member_required(login_url='admin_login')
@never_cache
def admin_add_product(request):
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

    return render(request, 'admin/product_add.html', {
        'product_form': product_form,
        'variant_form': variant_form,
        'image_form': image_form,
        'form_errors': form_errors  
    })

# ADMIN EDITING THE PRODUCT,Variant AND IMAGES
@staff_member_required(login_url='admin_login')
@never_cache
def admin_edit_product(request,product_id):
    
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
                if not variants and not variant_form.deleted_objects:
                    raise ValidationError('At least one variant is required.')
                for variant in variants:
                    variant.product = product
                    variant.save()
                for obj in variant_form.deleted_objects:
                    obj.delete()
                    # HANDLING IMAGES
                images = image_form.save(commit=False)
               
                deleted_ids = [img.id for img in image_form.deleted_objects if img and img.id]
                existing_images = ProductImage.objects.filter(product=product).exclude(id__in=deleted_ids)
                
                new_images = [img for img in images if img.image]  # Only images with new uploads
                total_images = len(existing_images) + len(new_images)
                # Delete images marked for deletion
                for obj in image_form.deleted_objects:
                    obj.delete()
                # Save new images
                for image in new_images:
                    image.product = product
                    image.save()
                # Check total images after processing
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

    return render(request, 'admin/product_edit.html', {
        'product_form': product_form,
        'variant_form': variant_form,
        'image_form': image_form,
        'form_errors': form_errors,
        'product': product,
    })


# ADMIN HIDING AND SHOWING EXISTING PRODUCTS
@staff_member_required(login_url='admin_login')
@never_cache
def admin_hide_product(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.method == "POST":
        variant.is_active = not variant.is_active
        variant.save()
        messages.success(request, f"Product '{variant.product.name}' is now {'visible' if variant.is_active else 'hidden'}.")

    return redirect('admin_product_list')

#################################################################################################################################

# ADMIN ORDER MANAGEMENT
@staff_member_required(login_url='admin_login')
def admin_order_list(request):
    query = request.GET.get('q', '').strip()
    orders = Order.objects.all().order_by('-created_at')   # ✅ note the ()
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

    context = {
        'query': query,
        'orders': page_obj,
        'order_count':order_count,
    }
    return render(request, 'admin/admin_order_list.html', context)



@staff_member_required(login_url='admin_login')
def admin_order_item_list(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()
    context = {'order': order, 'items': items}
    return render(request, 'admin/admin_order_item_list.html', context)


@staff_member_required(login_url='admin_login')
@never_cache
def admin_edit_order_status(request, item_id):
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
    
    return_requests= ReturnRequest.objects.all().select_related('order_item__order','order_item__variant')
    context= {'return_requests':return_requests}
    return render(request,'admin/admin_return_request_list.html',context)

@staff_member_required(login_url='admin_login')
def admin_return_approval(request,request_id):
    return_request=get_object_or_404(ReturnRequest,id=request_id)
    item=return_request.order_item
    order= item.order

    if request.method=='POST':
        action= request.POST.get('action')
        try:
            with transaction.atomic():
                if action=='APPROVE':
                    # Update return request
                    return_request.status = 'APPROVED'
                    return_request.save()

                    # Update Order item
                    item.status = 'RETURNED'
                    item.delivery_status = 'RETURNED'
                    item.return_reason = return_request.reason
                    item.return_other_reason = return_request.other_reason
                    item.save()

                    # Restore stock
                    item.variant.stock += item.quantity
                    item.variant.save()

                    # SHARING PRICE OF EACH ITEM IN THE ORDER
                    item_total = item.quantity * item.price
                    actual_order_total= sum(it.price * it.quantity for it in order.items.all()) # BEFORE COUPON APPLIED
                    paid_order_total= order.total_amount  # AFTER ANY COUPON APPLIED
                # PAID AMOUNT OF EACH ITEM IF COUPON IS APPLIED
                    refund_amount= (item_total/actual_order_total)* paid_order_total if actual_order_total > 0 else 0
                    refund_amount = Decimal(refund_amount).quantize(Decimal("0.01"))

                    order.total_amount = max(0, order.total_amount - refund_amount)
                    order.save()

                    # Credit refund to Users Wallet
                    wallet,created= Wallet.objects.get_or_create(user=order.user)
                    wallet.balance += Decimal(refund_amount).quantize(Decimal("0.01"))
                    wallet.save()

                    messages.success(request, f'The return request for # {item.id} is approved. Amount of {refund_amount} is added to the users wallet')
                elif action == 'DENY':
                    return_request.status = 'DENIED'
                    return_request.save()
                    messages.warning(request, f'The request for item # {item.id} is denied.')

                return redirect('admin_request_list')
        except Exception as e:
            messages.error(request, f'Error occured in Return request: {str(e)}')
            return redirect('admin_request_list')     
        
           
    
    return render(request,'admin/admin_return_approval.html',{'return_request':return_request, 'item':item, 'order':order} )

#################################################################################################################################

# ADMIN COUPON MANAGEMENT


@staff_member_required(login_url='admin_login')
def admin_coupon_list(request):
    # Get all coupons
    coupons = Coupon.objects.all().order_by('-created_at')
    
    # Handle search query
    query = request.GET.get('q', '')
    if query:
        coupons = coupons.filter(
            Q(coupon_code__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Paginate results
    paginator = Paginator(coupons, 4)  # Show 10 coupons per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare context
    context = {
        'coupons': page_obj,
        'coupon_count': paginator.count,
        'query': query,
    }
    
    return render(request, 'admin/admin_coupon_list.html', context)


@staff_member_required(login_url='admin_login')
def admin_coupon_creation(request):
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
    return render(request,'admin/admin_coupon_creation.html',{'form': form})

@staff_member_required(login_url='admin_login')
def admin_coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, f"Coupon '{coupon.coupon_code}' deleted successfully.")
        return redirect('admin_coupon_list')
    
    messages.warning(request, "Invalid request method.")
    return redirect('admin_coupon_list')


#################################################################################################################################

# ADMIN OFFER MANAGEMENT


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

    paginator = Paginator(offers, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'offers': page_obj,
        'offer_count': paginator.count,
        'query': query,
    }

    return render(request, 'admin/admin_offer_list.html', context)

@staff_member_required(login_url='admin_login')
def admin_offer_creation(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Offer created successfully!')
            return redirect('admin_offer_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = OfferForm()

    return render(request, 'admin/admin_offer_creation.html', {'form': form})

@staff_member_required(login_url='admin_login')
def admin_offer_delete(request,offer_id):
    offer= get_object_or_404(Offer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request,f'Offer {offer.name} deleted successfully.')
        return redirect('admin_offer_list')
    messages.error(request,'Invalid request method.')
    return redirect('admin_offer_list')


# SALES REPORT OF THE WEBSITE
@staff_member_required(login_url='admin_login')
def admin_sales_report(request):
    # ---------------- FILTER RANGE ---------------- #
    filter_type = request.GET.get('filter', 'daily')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    now = timezone.now()
    orders = Order.objects.filter(is_paid=True)

    # ---------------- DATE FILTER LOGIC ---------------- #
    if filter_type == 'daily':
        start = now - timedelta(days=1)
        orders = orders.filter(created_at__gte=start)
        group_by = TruncDay('created_at')
    elif filter_type == 'weekly':
        start = now - timedelta(weeks=1)
        orders = orders.filter(created_at__gte=start)
        group_by = TruncWeek('created_at')
    elif filter_type == 'monthly':
        start = now - timedelta(days=30)
        orders = orders.filter(created_at__gte=start)
        group_by = TruncMonth('created_at')
    elif filter_type == 'yearly':
        start = now - timedelta(days=365)
        orders = orders.filter(created_at__gte=start)
        group_by = TruncYear('created_at')
    elif filter_type == 'custom' and start_date and end_date:
        orders = orders.filter(created_at__date__range=[start_date, end_date])
        group_by = TruncDay('created_at')
    else:
        group_by = TruncDay('created_at')

    # ---------------- AGGREGATION ---------------- #
    # JOIN OrderItem to calculate offer-based discounts
    order_items = OrderItem.objects.filter(order__in=orders)

    # OFFER discount = (variant.original_price - variant.final_price)
    offer_discount_expr = ExpressionWrapper(
        (F('variant__price') - F('price')) * F('quantity'),
        output_field=DecimalField(max_digits=10, decimal_places=2)
    )

    sales_summary = order_items.aggregate(
        total_sales=Sum(F('price') * F('quantity')),
        total_offer_discount=Sum(offer_discount_expr),
        total_orders=Count('order', distinct=True),
        total_items_sold=Sum('quantity')
    )

    total_coupon_discount = Decimal('0.00')
    # If you store coupon info per order in session, use it to adjust here if needed
    # (We assume total_amount already includes coupon deduction)
    # You can track approximate coupon discount as (selling price before coupon - total_amount)
    # If you later add a coupon_discount field to Order, replace this logic directly.
    # For now, we’ll just compute order_total from Order.total_amount
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # ---------------- GROUPED DATA FOR CHART ---------------- #
    grouped_sales = (
        orders.annotate(period=group_by)
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('period')
    )

    context = {
        'filter_type': filter_type,
        'orders': orders.select_related('user'),
        'sales_summary': sales_summary,
        'total_revenue': total_revenue,
        'total_coupon_discount': total_coupon_discount,
        'grouped_sales': grouped_sales,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'admin/admin_sales_report.html', context)


