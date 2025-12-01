from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db import transaction,IntegrityError
from django.db.models import Q
from .models import Order, OrderItem,ReturnRequest
from ecomproducts.models import Categories, Product, ProductImage, ProductVariant,Coupon
from ecomusers.models import User, UserAddress, CartProducts,Wallet,WalletTransaction
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.conf import settings
import razorpay
from django.views.decorators.csrf import csrf_exempt

# def create_razorpay_order(amount, user_id, checkout_type='cart'):
#     """
#     Create a Razorpay order with comprehensive configuration
#     """
#     razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
#     order_data = {
#         'amount': int(amount * 100),  # Convert to paise
#         'currency': 'INR',
#         'payment_capture': '1',  # Auto capture payment
#         'notes': {
#             'order_type': 'ecommerce',
#             'user_id': str(user_id),
#             'checkout_type': checkout_type,
#             'platform': 'web'
#         }
#     }
    
#     try:
#         razorpay_order = razorpay_client.order.create(order_data)
#         return razorpay_order
#     except Exception as e:
#         print(f"Error creating Razorpay order: {str(e)}")
#         raise e

@login_required(login_url='login')
def buy_now(request, variant_id):
    ''' FOR SINGLE PRODUCT PURCHASE FROM A PRODUCT CARD. GETTING QUANTITY AND SELECT ADDRESS FOR DELIVERY. '''
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)

        if variant.stock <1:        
            messages.error(request,f'Product {variant} is out of stock. Please try again later.')
            return redirect(request.META.get('HTTP_REFERER','product_listing'))
        
        if request.method == 'POST':
            
            quantity = int(request.POST.get('quantity', 1))
            
            if quantity < 1:
                messages.error(request, "Quantity must be at least 1.")
                return redirect('buy_now', variant_id=variant_id)
                
            if quantity > variant.stock:        
                messages.error(request, f"Only {variant.stock} items available in stock.")
                return redirect('buy_now', variant_id=variant_id)

            
            request.session['buy_now_order_data'] = {
                'variant_id': variant.id,
                'quantity': quantity,
                'unit_price': str(variant.final_price),
                'total_price': str(quantity * variant.final_price),
                'is_cart_checkout': False,
            }
            print(f'order data: {request.session['buy_now_order_data']}')
            return redirect('checkout')
            
        context = {
            'variant': variant,
            'max_quantity': min(variant.stock, 5),
            'total_price': variant.final_price,
            'active_offer': variant.active_offer,
        }
        return render(request, 'user/buynow_quantity_select.html', context)
    except IntegrityError:
        messages.error(request, f'Something went wrong. Please try again.')
        return redirect(request.META.get('HTTP_REFERER','product_listing'))
    except Exception as e:
        messages.error(request,f"Unexcpected error occured: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER','product_listing'))
    

@login_required(login_url='login')
def checkout(request):
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
        'amount_payable': amount_payable,
        'estimated_delivery_date': estimated_delivery_date,
        'addresses': addresses,
        'default_address': default_address,
    }
    return render(request, 'user/checkout.html', context)


@never_cache
@login_required(login_url='login')
def payment_method(request):
    if 'order_data' not in request.session:
        messages.error(request, "No order data found. Please start over.")
        return redirect('product_listing')
    
    order_data = request.session['order_data']
    is_cart_checkout = order_data.get('is_cart_checkout', False)

    cart_price_data = request.session.get('cart_price_data', {})
    cart_item_details = cart_price_data.get('cart_item_details', [])

    if is_cart_checkout:
        cart_items = order_data['cart_items']
        variants = []
        for item in cart_items:
            variant = get_object_or_404(ProductVariant, id=item['variant_id'])
            quantity = item['quantity']

            # match with cart_item_details for unit_price
            detail = next((d for d in cart_item_details if d['variant_id'] == item['variant_id']), None)
            unit_price = Decimal(detail['unit_price']) if detail else Decimal(item['price'])
            item_total = Decimal(detail['item_total']) if detail else unit_price * quantity

            variants.append({
                'variant': variant,
                'quantity': quantity,
                'price': unit_price,
                'item_total': item_total
            })

        total_amount = Decimal(order_data['total_amount'])
        address = get_object_or_404(UserAddress, id=order_data['address_id'], user=request.user)

    else:  # Buy Now case
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
        address = "get_object_or_404(UserAddress, id=order_data['address_id'], user=request.user)"

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'COD')

        if payment_method in ['COD', 'WALLET']:
            try:
                with transaction.atomic():
                    # stock check
                    for item in variants:
                        if item['variant'].stock < item['quantity']:
                            messages.error(request, f"Insufficient stock for {item['variant']}.")
                            return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=item['variant'].id)

                    if payment_method == 'WALLET':
                        wallet, _ = Wallet.objects.get_or_create(user=request.user)
                        if wallet.balance < total_amount:
                            messages.error(request, 'Insufficient wallet balance.')
                            return redirect('user_wallet_page')
                        wallet.balance -= total_amount
                        wallet.save()
                        WalletTransaction.objects.create(
                            wallet= wallet,
                            transaction_type= 'DEBIT',
                            amount= total_amount,
                            description= 'Wallet Payment '
                        )


                    # create order
                    order = Order.objects.create(
                        user=request.user,
                        address=address,
                        total_amount=total_amount,
                        payment_method=payment_method,
                        is_paid=(payment_method == 'WALLET')
                    )

                    # create order items
                    # Create separate order items for each quantity purchased
                    for item in variants:
                        for _ in range(item['quantity']):
                            OrderItem.objects.create(
                                order=order,
                                variant=item['variant'],
                                quantity=1,  # Each record represents one item
                                price=item['price'],  # Per-unit price (after discount/offer)
                                status='ACTIVE',
                                delivery_status='PENDING'
                            )
                        # Deduct stock for the total quantity purchased
                        item['variant'].stock -= item['quantity']
                        item['variant'].save()


                    if is_cart_checkout:
                        CartProducts.objects.filter(user=request.user).delete()

                    # increment coupon usage
                    applied_coupon_code = cart_price_data.get('applied_coupon')
                    if applied_coupon_code:
                        try:
                            coupon = Coupon.objects.get(coupon_code=applied_coupon_code, is_active=True)
                            coupon.total_usage += 1
                            coupon.save()
                            if 'applied_coupon' in request.session:
                                del request.session['applied_coupon']
                        except Coupon.DoesNotExist:
                            pass

                    del request.session['order_data']
                    return redirect('order_success', order_id=order.id)

            except Exception as e:
                messages.error(request, f"Error processing order: {str(e)}")
                return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=variants[0]['variant'].id)

        # elif payment_method == 'RAZORPAY':
            # try:
            #     razorpay_order = create_razorpay_order(
            #         total_amount, 
            #         request.user.id, 
            #         'cart' if is_cart_checkout else 'buy_now'
            #     )
            # except Exception as e:
            #     messages.error(request, f"Failed to create payment order: {str(e)}")
            #     return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=variants[0]['variant'].id)
            # order_data_with_total = order_data.copy()
            # order_data_with_total['total_amount'] = str(total_amount)
            # request.session[f'razorpay_pending_{razorpay_order["id"]}'] = order_data_with_total
            # return render(request, 'user/razorpay_checkout.html', {
            #     'variants': variants,
            #     'total_amount': total_amount,
            #     'address': address,
            #     'is_cart_checkout': is_cart_checkout,
            #     'razorpay_order_id': razorpay_order['id'],
            #     'razorpay_key': settings.RAZORPAY_KEY_ID,
            #     'razorpay_amount': int(total_amount * 100),
            # })
            pass

    return render(request, 'user/payment_method.html', {
        'variants': variants,
        'total_amount': total_amount,
        'address': address,
        'is_cart_checkout': is_cart_checkout
    })



@csrf_exempt
def razorpay_success(request):
    if request.method == "POST":
        data = request.POST
        razorpay_order_id = data.get('razorpay_order_id')
        payment_id = data.get('razorpay_payment_id')
        signature = data.get('razorpay_signature')

        pending_key = f'razorpay_pending_{razorpay_order_id}'
        pending_data = request.session.get(pending_key)
        if not pending_data:
            messages.error(request, "No pending order found.")
            return redirect('product_listing')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            # Verify payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            
            # Fetch payment details to get payment method used
            payment_details = client.payment.fetch(payment_id)
            payment_method_used = payment_details.get('method', 'unknown')
            
            print(f"Payment successful - Method: {payment_method_used}, Order ID: {razorpay_order_id}")

            order_data = pending_data
            is_cart_checkout = order_data.get('is_cart_checkout', False)
            total_amount = Decimal(order_data['total_amount'])
            address = get_object_or_404(UserAddress, id=order_data['address_id'], user=request.user)
            cart_price_data = request.session.get('cart_price_data', {})
            cart_item_details = cart_price_data.get('cart_item_details', [])

            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    total_amount=total_amount,
                    payment_method='RAZORPAY',
                    is_paid=True,
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=payment_id,
                    razorpay_signature=signature
                )

                if is_cart_checkout:
                    for item in order_data['cart_items']:
                        variant = get_object_or_404(ProductVariant, id=item['variant_id'])
                        quantity = item['quantity']
                        detail = next((d for d in cart_item_details if d['variant_id'] == item['variant_id']), None)
                        unit_price = Decimal(detail['unit_price']) if detail else Decimal(item['price'])

                        if variant.stock < quantity:
                            raise Exception(f"Insufficient stock for {variant}.")
                        for _ in range(quantity):
                            OrderItem.objects.create(
                                order=order,
                                variant=variant,
                                quantity=1,
                                price=unit_price,  # ✅ per-unit final price
                                status='ACTIVE',
                                delivery_status='PENDING'
                            )
                        variant.stock -= quantity
                        variant.save()
                    CartProducts.objects.filter(user=request.user).delete()
                else:
                    variant = get_object_or_404(ProductVariant, id=order_data['variant_id'])
                    quantity = order_data['quantity']
                    price = Decimal(order_data['price'])
                    if variant.stock < quantity:
                        raise Exception(f"Insufficient stock for {variant}.")
                    for _ in range(quantity):
                        OrderItem.objects.create(
                            order=order,
                            variant=variant,
                            quantity=1,
                            price=price,
                            status='ACTIVE',
                            delivery_status='PENDING'
                        )
                        variant.stock -= quantity
                        variant.save()

                # increment coupon usage
                applied_coupon_code = cart_price_data.get('applied_coupon')
                if applied_coupon_code:
                    try:
                        coupon = Coupon.objects.get(coupon_code=applied_coupon_code, is_active=True)
                        coupon.total_usage += 1
                        coupon.save()
                        if 'applied_coupon' in request.session:
                            del request.session['applied_coupon']
                    except Coupon.DoesNotExist:
                        pass

                # cleanup
                if 'order_data' in request.session:
                    del request.session['order_data']
                del request.session[pending_key]

                return redirect('order_success', order_id=order.id)

        except razorpay.errors.SignatureVerificationError as e:
            print(f"Signature verification failed: {str(e)}")
            messages.error(request, "Payment verification failed. Please try again.")
            if pending_key in request.session:
                del request.session[pending_key]
            return redirect('product_listing')
        except razorpay.errors.BadRequestError as e:
            print(f"Razorpay bad request error: {str(e)}")
            messages.error(request, "Payment request failed. Please try again.")
            if pending_key in request.session:
                del request.session[pending_key]
            return redirect('product_listing')
        except Exception as e:
            print(f"Unexpected error during payment processing: {str(e)}")
            messages.error(request, f"Payment processing failed: {str(e)}")
            if pending_key in request.session:
                del request.session[pending_key]
            return redirect('product_listing')


@never_cache
@login_required(login_url='login')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'user/order_success.html', context)

@login_required(login_url='login')
def order_error(request):
    # No order_id needed for general payment errors
    context = {
        'order': None,
    }
    return render(request, 'user/order_error.html', context)


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

    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Orders', 'url': ''}
    ]
    return render(request, 'user/order_list.html', {
        'query': query,
        'status_filter': status_filter,
        'orders': page_obj if not query else None,  # only if query is empty
        'items': page_obj if query else None,       # only if query exists
        'page_obj': page_obj,
        'breadcrumbs': breadcrumbs
    })


@login_required(login_url='login')
def order_details(request, order_id, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user, order__id=order_id)
    
    breadcrumbs=[
        {'name': 'Home', 'url':'login_home'},
        {'name': 'Orders', 'url': 'order_list'},
        {'name': 'Order details', 'url':''}
    ]
    context = {
        'order_item': order_item,
        'breadcrumbs': breadcrumbs
    }
    return render(request, 'user/order_details.html', context)

@never_cache
@login_required(login_url='login')
def cancel_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)
    wallet,created= Wallet.objects.get_or_create(user= request.user)

    if request.method == 'POST':
        selected_reason = request.POST.get("reason")
        other_reason_text = request.POST.get("other_reason", "").strip()

        try:
            with transaction.atomic():
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

                # Mark as cancelled
                item.status = 'CANCELLED'
                item.delivery_status = 'CANCELLED'
                item.cancellation_reason = selected_reason
                if selected_reason == "OTHER":
                    item.other_reason = other_reason_text
                item.save()
        # WALLET REFUND IF THE PAYMENT VIA WALLET OR RAZORPAY
                if order.payment_method in ['WALLET', 'RAZORPAY']:
                    wallet.balance += Decimal(refund_amount).quantize(Decimal("0.01"))
                    wallet.save()

                    WalletTransaction.objects.create(
                        wallet= wallet,
                        transaction_type= 'CREDIT',
                        amount= Decimal(refund_amount),
                        description= 'Order Cancel Refund'
                    )
                # Cancel entire order if all items are cancelled
                if not order.items.filter(status='ACTIVE').exists():
                    order.status = 'CANCELLED'
                    order.total_amount = Decimal('0.00')
                    order.save()
                    messages.success(request, "Order cancelled as all items were removed.")
                    return redirect('order_list')                

                order.save()
                messages.success(request, f"Item {item.variant} cancelled successfully.")
                return redirect('order_details', order_id=order.id, item_id=item.id)

        except Exception as e:
            messages.error(request, f"Error cancelling item: {str(e)}")
            return redirect('order_details', order_id=order.id, item_id=item.id)

    return render(request, "user/cancel_order_item.html", {"item": item, "order": order})

@never_cache
@login_required(login_url='login')
def return_order_item(request, order_id, item_id):
    # Get the order and item based on IDs
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    # Ensure the item is delivered before allowing the return
    if item.delivery_status != 'DELIVERED':
        messages.error(request, "This item cannot be returned as it has not been delivered.")
        return redirect('order_details', order_id=order.id)

    # Handle the return process
    if request.method == 'POST':
        reason=request.POST.get('reason')
        other_reason= request.POST.get('other_reason')
        try:
            with transaction.atomic():
            # CHECK IF A RETURN REQUEST IS ALREADY THERE
                if ReturnRequest.objects.filter(order_item=item).exists():
                    messages.warning(request,'The return request for the same product is already made.')
                    return redirect('order_details', order_id=order.id, item_id=item.id)
                # CREATE A RETURN REQUEST
                ReturnRequest.objects.create(
                    order_item= item,
                    reason= reason,
                    other_reason= other_reason,
                    status='PENDING'
                )
                messages.success(request, f'The return request for {item.variant} is submitted and waiting for the Admin approval')
                return redirect('order_details', order_id=order.id, item_id=item.id)
        
        except Exception as e:
            messages.error(request, f"Error returning item: {str(e)}")
            return redirect('order_details', order_id=order.id, item_id=item.id)

    return render(request, "user/return_order_item.html", {"order": order, "item": item})