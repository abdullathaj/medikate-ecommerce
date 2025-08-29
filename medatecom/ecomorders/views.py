from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db import transaction,IntegrityError
from django.db.models import Q
from .models import Order, OrderItem
from ecomproducts.models import Categories, Product, ProductImage, ProductVariant
from ecomusers.models import User, UserAddress, CartProducts
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.paginator import Paginator

@login_required(login_url='login')
def buy_now(request, variant_id):
    ''' FOR SINGLE PRODUCT PURCHASE FROM A PRODUCT CARD. GETTING QUANTITY AND SELECT ADDRESS FOR DELIVERY. '''
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)

        if variant.stock <1:         # IF PRODUCT OUT OF STOCK
            messages.error(request,f'Product {variant} is out of stock. Please try again later.')
            return redirect(request.META.get('HTTP_REFERER','product_listing'))
        
        if request.method == 'POST':
            # GETTING QUANTITY OF PRODUCT FROM TEMPLATE
            quantity = int(request.POST.get('quantity', 1))
            address_id = request.POST.get('address_id')
            
            if quantity < 1:
                messages.error(request, "Quantity must be at least 1.")
                return redirect('buy_now', variant_id=variant_id)
                
            if quantity > variant.stock:        
                messages.error(request, f"Only {variant.stock} items available in stock.")
                return redirect('buy_now', variant_id=variant_id)
                
            if not address_id:
                messages.error(request, "Please select a delivery address Or add a new address.")
                return redirect('buy_now', variant_id=variant_id)
                
            address = get_object_or_404(UserAddress, id=address_id, user=request.user)
            
            request.session['order_data'] = {
                'variant_id': variant.id,
                'quantity': quantity,
                'price': str(variant.price),
                'address_id': address_id,
                'is_cart_checkout': False,
            }
            return redirect('payment_method')
            
        addresses = UserAddress.objects.filter(user=request.user)
        context = {
            'variant': variant,
            'max_quantity': min(variant.stock, 10),
            'addresses': addresses,
            'total_price': variant.price
        }
        return render(request, 'user/order_quantity_address_select.html', context)
    except IntegrityError:
        messages.error(request, f'Something went wrong. Please try again.')
        return redirect(request.META.get('HTTP_REFERER','product_listing'))
    except Exception as e:
        messages.error(request,f"Unexcpected error occured: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER','product_listing'))
    

@login_required(login_url='login')
def cart_checkout(request):
    ''' MULTI PRODUCT PURCHASE FROM CART. SELECT ADDRESS FOR DELIVERY. '''

    cart_items = CartProducts.objects.filter(
        user=request.user,
        variant__is_active=True
    ).select_related('variant__product')
    
    if not cart_items:
        messages.error(request, "Your cart is empty. Add items to proceed.")
        return redirect('user_cart_page')
    
    # Retrieve price data from session
    cart_price_data = request.session.get('cart_price_data', {})
    if not cart_price_data:
        messages.error(request, "Cart data is missing. Please revisit your cart.")
        return redirect('user_cart_page')
    
    # Convert string values back to Decimal
    original_total_price = Decimal(cart_price_data.get('original_total_price', '0'))
    selling_total_price = Decimal(cart_price_data.get('selling_total_price', '0'))
    discount_total = Decimal(cart_price_data.get('discount_total', '0'))
    taxes = Decimal(cart_price_data.get('taxes', '0'))
    amount_payable = Decimal(cart_price_data.get('amount_payable', '0'))
    
    # Attach per-item calculations to cart items
    cart_item_details = cart_price_data.get('cart_item_details', [])
    for item in cart_items:
        if item.quantity > item.variant.stock:
            messages.error(request, f"Insufficient stock for {item.variant}. Only {item.variant.stock} available.")
            return redirect('user_cart_page')
        for detail in cart_item_details:
            if detail['variant_id'] == item.variant.id and detail['quantity'] == item.quantity:
                item.item_total = Decimal(detail['item_total'])
                item.item_discount = Decimal(detail['item_discount'])
                break
        else:
            messages.warning(request, "Cart data is outdated. Please revisit your cart.")
            return redirect('user_cart_page')
    
    estimated_delivery_date = (datetime.now() + timedelta(days=7)).strftime('%B %d, %Y')
    
    # Fetch addresses
    addresses = UserAddress.objects.filter(user=request.user)
    if not addresses.exists():
        messages.warning(request, "Please add a delivery address before checkout.")
        return redirect('user_profile_update')  # <-- Redirect to profile edit if no address found

    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        
        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect('cart_checkout')
            
        address = get_object_or_404(UserAddress, id=address_id, user=request.user)
        
        request.session['order_data'] = {
            'cart_items': [
                {
                    'variant_id': item.variant.id,
                    'quantity': item.quantity,
                    'price': str(item.variant.price)
                } for item in cart_items
            ],
            'address_id': address_id,
            'total_amount': str(amount_payable),
            'is_cart_checkout': True
        }
        return redirect('payment_method')
    
    addresses = UserAddress.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    
    context = {
        'cart_items': cart_items,
        'original_total_price': original_total_price,
        'selling_total_price': selling_total_price,
        'discount_total': discount_total,
        'taxes': taxes,
        'amount_payable': amount_payable,
        'estimated_delivery_date': estimated_delivery_date,
        'addresses': addresses,
        'default_address': default_address,
    }
    return render(request, 'user/cart_checkout.html', context)

@never_cache
@login_required(login_url='login')
def payment_method(request):
    ''' SELECT PAYMENT METHOD FOR PURCHASE. '''

    if 'order_data' not in request.session:
        messages.error(request, "No order data found. Please start over.")
        return redirect('product_listing')
    
    order_data = request.session['order_data']
    is_cart_checkout = order_data.get('is_cart_checkout', False)
    
    if is_cart_checkout:
        cart_items = order_data['cart_items']
        cart_price_data = request.session.get('cart_price_data', {})
        cart_item_details = cart_price_data.get('cart_item_details', [])
        variants = [
            {
                'variant': get_object_or_404(ProductVariant, id=item['variant_id']),
                'quantity': item['quantity'],
                'price': Decimal(item['price']),
                'item_total': next(
                    (Decimal(detail['item_total']) for detail in cart_item_details 
                     if detail['variant_id'] == item['variant_id'] and detail['quantity'] == item['quantity']),
                    Decimal(item['price']) * item['quantity']
                )
            } for item in cart_items
        ]
        total_amount = Decimal(order_data['total_amount'])
        address = get_object_or_404(UserAddress, id=order_data['address_id'], user=request.user)
    else:
        variant = get_object_or_404(ProductVariant, id=order_data['variant_id'])
        quantity = order_data['quantity']
        price = Decimal(order_data['price'])
        variants = [{
            'variant': variant,
            'quantity': quantity,
            'price': price,
            'item_total': price * quantity
        }]
        total_amount = price * quantity
        address = get_object_or_404(UserAddress, id=order_data['address_id'], user=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'COD')
        if payment_method != 'COD':
            messages.error(request, "Only Cash on Delivery is available.")
            return redirect('payment_method')
            
        try:
            with transaction.atomic():
                for item in variants:
                    if item['variant'].stock < item['quantity']:
                        messages.error(request, f"Insufficient stock for {item['variant']}.")
                        return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=item['variant'].id)
                
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    total_amount=total_amount,
                    payment_method='COD',
                    # status='PENDING',
                    is_paid=False
                )
                print(f'order {order} created with {order.payment_method} toral payment is {total_amount}')                
                
                for item in variants:
                    for _ in range(item['quantity']):  # EACH QUANTITY CREATE EACH ORDER ITEM
                        OrderItem.objects.create(
                            order=order,
                            variant=item['variant'],
                            quantity= 1,
                            price=item['price'],
                            status='ACTIVE',
                            delivery_status='PENDING'
                        )
                        item['variant'].stock -= 1
                        item['variant'].save()
                for item in OrderItem.objects.filter(order=order):
                    print(f'ordered items are: {item.variant} x {item.quantity} @ {item.total_price} with {item.delivery_status}')
                
                if is_cart_checkout:
                    CartProducts.objects.filter(user=request.user).delete()
                
                del request.session['order_data']
                
                return redirect('order_success', order_id=order.id)
                
        except Exception as e:
            messages.error(request, f"Error processing order: {str(e)}")
            return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=variants[0]['variant'].id)
    
    context = {
        'variants': variants,
        'total_amount': total_amount,
        'address': address,
        'is_cart_checkout': is_cart_checkout
    }
    return render(request, 'user/payment_method.html', context)

@never_cache
@login_required(login_url='login')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'user/order_success.html', context)


@login_required(login_url='login')
def orderlist(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()  # new filter param
    
    if query:
        # Search directly in OrderItem
        items = OrderItem.objects.filter(
            order__user=request.user
        ).filter(
            Q(variant__variant_name__icontains=query) |
            Q(variant__product__name__icontains=query) |
            Q(variant__product__brand__icontains=query) |
            Q(variant__product__category__name__icontains=query)
        )
        
        # Apply delivery status filter if provided
        if status_filter:
            if status_filter.upper() == "CANCELLED":
                items = items.filter(Q(status="CANCELLED") | Q(delivery_status="CANCELLED"))
            else:
                items = items.filter(delivery_status=status_filter.upper())

        items = items.select_related("order", "variant", "variant__product").distinct()
        print('Only Showing the Items with filtered status.')
        for i in items:
            print(i.variant,i.delivery_status)
        
        paginator = Paginator(items, 10)
    else:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        # Apply delivery status filter on items inside orders
        if status_filter:
            orders = orders.filter(items__delivery_status=status_filter.upper()).distinct()
            print('Showing the co-odered items delivery status also.')
            for order in orders:
                print(f"\nOrder #{order.id} - {order.user.username}")
                for item in order.items.all():
                    print(f"   Item: {item.variant} | Delivery Status: {item.display_status}")
        
        paginator = Paginator(orders, 5)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user/order_list.html', {
        'query': query,
        'status_filter': status_filter,
        'orders': page_obj if not query else None,  # only if query is empty
        'items': page_obj if query else None,       # only if query exists
        'page_obj': page_obj,
    })


@login_required(login_url='login')
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'user/order_details.html', context)

@never_cache
@login_required(login_url='login')
def cancel_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if request.method == 'POST':
        selected_reason = request.POST.get("reason")
        other_reason_text = request.POST.get("other_reason", "").strip()

        try:
            with transaction.atomic():
                # Restore stock
                item.variant.stock += item.quantity
                item.variant.save()

                # Update order total
                item_total = item.quantity * item.price
                order.total_amount = max(0, order.total_amount - item_total)

                # Mark as cancelled
                item.status = 'CANCELLED'
                item.delivery_status = 'CANCELLED'
                item.cancellation_reason = selected_reason
                if selected_reason == "OTHER":
                    item.other_reason = other_reason_text
                item.save()

                # Cancel entire order if all items are cancelled
                if not order.items.filter(status='ACTIVE').exists():
                    order.status = 'CANCELLED'
                    order.total_amount = Decimal('0.00')
                    order.save()
                    messages.success(request, "Order cancelled as all items were removed.")
                    return redirect('order_list')

                order.save()
                messages.success(request, f"Item {item.variant} cancelled successfully.")
                return redirect('order_details', order_id=order.id)

        except Exception as e:
            messages.error(request, f"Error cancelling item: {str(e)}")
            return redirect('order_details', order_id=order.id)

    return render(request, "user/cancel_order_item.html", {"item": item, "order": order})
