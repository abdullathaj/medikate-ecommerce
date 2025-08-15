from django.shortcuts import render,redirect,get_object_or_404
from ecomusers.models import User
from ecomproducts.models import Categories,Product,ProductVariant,ProductImage
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from .forms import Useraddform,CategoryAddForm,ProductAddForm,ProductImageForm,VariantAddForm,VariantFormset,ImageFormset
from django.db.models import Q
from django.contrib import messages
from django.forms import inlineformset_factory
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator




# Create your views here.

# DASHBOARD for Admin

# @staff_member_required
# @never_cache
def admin_dashboard(request):

    
    
    return render(request,'admin/dashboard.html')


# USER MANAGEMENT FOR ADMIN
# @staff_member_required
# @never_cache
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
# @staff_member_required
# @never_cache
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

# @staff_member_required
# @never_cache
def admin_block_user(request,user_id):
    user=get_object_or_404(User,id=user_id)
    if request.method=='POST' and not user.is_superuser:
        user.is_active=not user.is_active
        user.save()
        status='unblocked' if user.is_active else 'blocked'
        messages.success(request,f'User {user.username} has been {status}...')
    return redirect(admin_customer_details)


# ADMIN CATEGORY MANAGEMENT


# CATEGORY TABLE
# @staff_member_required
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
@staff_member_required
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
# @staff_member_required
# @never_cache 
def admin_hide_category(request, category_id):
    category = get_object_or_404(Categories, id=category_id)

    if request.method == "POST":
        category.is_active = not category.is_active
        category.save()
        messages.success(request, f"Category '{category.name}' is now {'visible' if category.is_active else 'hidden'}.")

    return redirect('admin_categories')


# ADMIN EDITING CATEGORIES
# @staff_member_required
# @never_cache
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
    


# ADMIN PRODUCT MANAGEMENT

# PRODUCT TABLE
# @staff_member_required
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
# @staff_member_required
# @never_cache
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
# @staff_member_required
# @never_cache
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
# @staff_member_required
# @never_cache
def admin_hide_product(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.method == "POST":
        variant.is_active = not variant.is_active
        variant.save()
        messages.success(request, f"Product '{variant.product.name}' is now {'visible' if variant.is_active else 'hidden'}.")

    return redirect('admin_product_list')

    