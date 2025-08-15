from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem
from ecomproducts.models import Categories, Product, ProductImage, ProductVariant
from ecomusers.models import User, UserAddress, CartProducts
from django.db import transaction
from decimal import Decimal


# Create your views here.

@login_required(login_url='login')
def buy_now(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        address_id = request.POST.get('address_id')
        
        # Validate quantity
        if quantity < 1:
            messages.error(request, "Quantity must be at least 1.")
            return redirect('buy_now', variant_id=variant_id)
            
        if quantity > variant.stock:
            messages.error(request, f"Only {variant.stock} items available in stock.")
            return redirect('buy_now', variant_id=variant_id)
            
        # Validate address
        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect('buy_now', variant_id=variant_id)
            
        address = get_object_or_404(UserAddress, id=address_id, user=request.user)
        
        # Store order data in session for payment step
        request.session['order_data'] = {
            'variant_id': variant.id,
            'quantity': quantity,
            'price': str(variant.price),
            'address_id': address_id
        }
        return redirect('payment_method')
        
    addresses = UserAddress.objects.filter(user=request.user)
    context = {
        'variant': variant,
        'max_quantity': min(variant.stock, 10),  # Limit max quantity to 10 or stock
        'addresses': addresses,
        'total_price': variant.price  # Initial total for one item
    }
    return render(request, 'user/order_quantity_address_select.html', context)


@login_required(login_url='login')
def payment_method(request):
    if 'order_data' not in request.session:
        messages.error(request, "No order data found. Please start over.")
        return redirect('product_list')
    
    order_data = request.session['order_data']
    variant = get_object_or_404(ProductVariant, id=order_data['variant_id'])
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'COD')
        if payment_method != 'COD':
            messages.error(request, "Only Cash on Delivery is available.")
            return redirect('payment_method')
            
        try:
            with transaction.atomic():
                # Verify stock again before creating order
                if variant.stock < order_data['quantity']:
                    messages.error(request, f"Insufficient stock for {variant}.")
                    return redirect('buy_now', variant_id=variant.id)
                
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    address_id=order_data['address_id'],
                    total_amount=Decimal(order_data['price']) * order_data['quantity'],
                    payment_method='COD',
                    status='PENDING',
                    is_paid=False
                )
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=order_data['quantity'],
                    price=variant.price
                )
                
                # Update stock
                variant.stock -= order_data['quantity']
                variant.save()
                
                # Clear session data
                del request.session['order_data']
                
                return redirect('order_success', order_id=order.id)
                
        except Exception as e:
            messages.error(request, f"Error processing order: {str(e)}")
            return redirect('buy_now', variant_id=variant.id)
    
    context = {
        'variant': variant,
        'quantity': order_data['quantity'],
        'total_price': Decimal(order_data['price']) * order_data['quantity'],
        'address': UserAddress.objects.get(id=order_data['address_id'])
    }
    return render(request, 'user/payment_method.html', context)



@login_required(login_url='login')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'user/order_success.html', context)

@login_required
def orderlist(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user/order_list.html', {'orders': orders})



@login_required(login_url='login')
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'user/order_details.html', context)