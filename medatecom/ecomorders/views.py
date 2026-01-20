from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
import json
from django.http import JsonResponse
from django.db import transaction,IntegrityError
from django.db.models import Q,F
from .models import Order, OrderItem,ReturnRequest
from ecomproducts.models import Categories, Product, ProductImage, ProductVariant,Coupon
from ecomusers.models import User, UserAddress, CartProducts,Wallet,WalletTransaction
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.conf import settings
import razorpay
from django.views.decorators.csrf import csrf_exempt
from .utils import render_to_pdf


@login_required(login_url='login')
def buy_now(request, variant_id):
    '''Single Variant Purchase with Multiple Qty.'''
    
    try:
        variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)

        if variant.stock < 1:
            messages.error(request, f'Product {variant} is out of stock.')
            return redirect(request.META.get('HTTP_REFERER', 'product_listing'))
        
        if request.method =='GET':
            request.session.pop('applied_coupon',None)
            request.session.pop('order_data',None)

        if request.method == 'POST':
            quantity = int(request.POST.get('quantity', 1))

            if quantity < 1:
                messages.error(request, "Quantity must be at least 1.")
                return redirect('buy_now', variant_id=variant_id)

            if quantity > variant.stock:
                messages.error(request, f"Only {variant.stock} items available.")
                return redirect('buy_now', variant_id=variant_id)

            total_price = quantity * variant.final_price  # with or without offer discount on Product or Category

            request.session['buy_now_order_data'] = {  # Session is passing to Checkout page along with Cart Data.
                'variant_id': variant.id,
                'quantity': quantity,
                'original_unit_price': str(variant.price), # item price
                'unit_price': str(variant.final_price),     # item final price
                'total_price': str(total_price),            # item final price * qty
                'is_cart_checkout': False,
            }

            return redirect('buynow_checkout')

        context = {
            'variant': variant,
            'max_quantity': min(variant.stock, 5),
            'total_price': variant.final_price,
            'active_offer': variant.active_offer,
        }
        return render(request, 'user/buynow_quantity_select.html', context)

    except IntegrityError:
        messages.error(request, 'Something went wrong. Please try again.')
        return redirect(request.META.get('HTTP_REFERER','product_listing'))

    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER','product_listing'))
    

@login_required(login_url='login')
@never_cache
def buynow_checkout(request):
    
    bn_data = request.session.get('buy_now_order_data')
    if not bn_data:
        messages.error(request, "Session expired. Please try buying the product again.")
        return redirect('product_listing')
    
    if request.method=='GET':
        request.session.pop('applied_coupon',None)
        request.session.pop('order_data',None)

    variant = get_object_or_404(ProductVariant, id=bn_data['variant_id'], is_active=True)
    quantity = int(bn_data['quantity'])
    
    
    total_before_coupon = Decimal(bn_data['total_price'])  # item final price * qty
    
    
    if quantity > variant.stock:
        messages.error(request, f"Insufficient stock. Only {variant.stock} left.")
        return redirect('product_details', variant_id=variant.id)

    
    applied_coupon = request.session.get('applied_coupon')
    print(f'Applied Coupon in Buynow: {applied_coupon}')
    if applied_coupon:
        final_payable = Decimal(applied_coupon['final_amount']) # discounted amount
    else:
        final_payable = total_before_coupon       # item final price * qty
    print(f'Final Payable: {final_payable}')

    
    if request.method == "POST":
        address_id = request.POST.get("address_id")
        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect('buynow_checkout')

        
        effective_unit_price = (final_payable / quantity).quantize(Decimal('0.01')) # User Paid price per item

        request.session['order_data'] = {
            'cart_items': [{
                'variant_id': variant.id,
                'quantity': quantity,
                'unit_price': str(effective_unit_price),  # User paid price per item
                'line_total': str(final_payable),         # User paid price for Total Order 
            }],
            'address_id': address_id,
            'total_amount': str(final_payable),           # User paid price for Total Order
            'coupon': applied_coupon['coupon_code'] if applied_coupon else None,
            'is_cart_checkout': False,
        }
        dictt={
            'cart_items': [{
                'variant_id': variant.id,
                'quantity': quantity,
                'unit_price': str(effective_unit_price), 
                'line_total': str(final_payable),
            }],
            'address_id': address_id,
            'total_amount': str(final_payable),
            'coupon': applied_coupon['coupon_code'] if applied_coupon else None,
            'is_cart_checkout': False,
        }
        print(f'Session Order data for buynow \n {dictt}')

        return redirect('payment_method')

    
    addresses = UserAddress.objects.filter(user=request.user)
    available_coupons = Coupon.objects.filter(
        is_active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now()
    ).exclude(Q(max_usage_limit__gt=0) & Q(total_usage__gte=F('max_usage_limit')))

    context = {
        'variant': variant,
        'quantity': quantity,
        'original_unit_price': bn_data['original_unit_price'],  # item price
        'mrp_total': variant.price * quantity, # Total MRP
        'product_offer_discount': (variant.price * quantity) - total_before_coupon, # Product Offer Discount
        'coupon_discount': Decimal(applied_coupon['coupon_discount']) if applied_coupon else Decimal('0.00'), # Coupon Discount
        'total_discount': (variant.price * quantity) - final_payable, # Total Savings
        'subtotal': total_before_coupon,       # Item final price * qty
        'final_payable': final_payable,       # User paid price for Total Order.
        'addresses': addresses,
        'default_address': addresses.filter(is_default=True).first(),
        'available_coupons': available_coupons,
        'estimated_delivery': (timezone.now() + timedelta(days=7)).date(),
    }
    return render(request, 'user/buynow_checkout.html', context)
 
@login_required(login_url='login')
@never_cache
def checkout(request):
    
    cart_items = CartProducts.objects.filter(
        user=request.user,
        variant__is_active=True
    ).select_related('variant__product')
    
    if not cart_items.exists():
        messages.error(request, "Your cart is empty. Add items to proceed.")
        return redirect('user_cart_page')
    
    if request.method == 'GET':
        request.session.pop('applied_coupon',None)
        request.session.pop('order_data',None)
    
    cart_price_data = request.session.get('cart_price_data', {})
    if not cart_price_data:
        messages.error(request, "Cart data is missing. Please revisit your cart.")
        return redirect('user_cart_page')
    
    original_total_price = Decimal(cart_price_data.get('original_total_price', '0'))  # sum of item price * qty
    selling_total_price = Decimal(cart_price_data.get('selling_total_price', '0'))     # sum of item finla price * qty
    discount_total = Decimal(cart_price_data.get('discount_total', '0'))
    amount_payable = Decimal(cart_price_data.get('amount_payable', '0'))             # Amount payable == selling totla price
    
    cart_item_details = cart_price_data.get('cart_item_details', [])

    
    for item in cart_items:
        if item.quantity > item.variant.stock:
            messages.error(request, f"Insufficient stock for {item.variant}. Only {item.variant.stock} available.")
            return redirect('user_cart_page')
        
        
        for detail in cart_item_details:
            if detail['variant_id'] == item.variant.id and detail['quantity'] == item.quantity:
                item.total_original_price = item.variant.price * item.quantity  # item price * qty
                item.total_selling_price = item.variant.final_price * item.quantity   # item final price * qty
                item.item_discount = (item.total_original_price - item.total_selling_price)
                item.item_total = Decimal(detail['item_total'])    # Item final price* qty in Cart model
                break
        else:
            messages.warning(request, "Cart data is outdated. Please revisit your cart.")
            return redirect('user_cart_page')
    
    
    addresses = UserAddress.objects.filter(user=request.user)
    if not addresses.exists():
        messages.warning(request, "Please add a delivery address before checkout.")
        return redirect('user_profile_update')  

    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        if not address_id:
            messages.error(request, "Please select a delivery address.")
            return redirect('checkout')
            
        selected_address = get_object_or_404(UserAddress, id=address_id, user=request.user)

        
        applied_coupon = request.session.get('applied_coupon')
        if applied_coupon:
            final_amount = Decimal(applied_coupon['final_amount'])    # discounted amount
            coupon_code = applied_coupon['coupon_code']
            discount_percent=applied_coupon['discount_percent']/Decimal('100')
            
            print(f'Coupon applied: {coupon_code}, final amount : {final_amount}')
        else:
            final_amount = amount_payable       # sum of item final price * qty
            coupon_code = None
            discount_percent=Decimal('0.00')

        order_items=[]
        calaculated_total=Decimal('0.00')
        for item in cart_items:
            base_unit_price= item.variant.final_price  
            paid_unit_price= (base_unit_price * (Decimal('1.00')- discount_percent)).quantize(Decimal('0.01'))  # Actual paid price per item
            line_total = paid_unit_price * item.quantity 
            calaculated_total+= line_total

            order_items.append({
                'variant_id':item.variant.id,
                'quantity': item.quantity,
                'unit_price':str(paid_unit_price),    # actual paid price per unit
                'line_total':str(line_total)            # unit price * qty
            })

        final_amount=calaculated_total.quantize(Decimal('0.01'))  

        request.session['order_data'] = {
            'cart_items': order_items,
            'address_id': address_id,
            'total_amount': str(final_amount),   # sum of all distributed item prices
            'coupon': coupon_code,
            'is_cart_checkout': True
        }
        
        
        return redirect('payment_method')
    
    
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now()
    ).exclude(
        Q(max_usage_limit__gt=0) & Q(total_usage__gte=F('max_usage_limit'))
    )
    
    

    context = {
        'cart_items': cart_items,
        'original_total_price': original_total_price,
        'selling_total_price': selling_total_price,
        'discount_total': discount_total,
        'amount_payable': amount_payable,
        'estimated_delivery_date': (datetime.now() + timedelta(days=7)).strftime('%B %d, %Y'),
        'addresses': addresses,
        'default_address': default_address,
        'available_coupons': available_coupons
    }
    return render(request, 'user/checkout.html', context)


@login_required
@never_cache
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code')
        coupon = Coupon.objects.filter(coupon_code=code).first()
        checkout_type= request.POST.get('checkout_type')

        if not coupon or not coupon.is_valid:
            return JsonResponse({'status': 'error', 'message': 'Invalid or expired coupon.'})

        
        if checkout_type == 'buy_now':
            if 'buy_now_order_data' not in request.session:
                return JsonResponse({'status': 'error', 'message': 'Buy Now session expired.'})
            amount = Decimal(request.session['buy_now_order_data']['total_price'])    # item final price * qty

        elif checkout_type == 'cart':
            if 'cart_price_data' not in request.session:
                return JsonResponse({'status': 'error', 'message': 'Cart session expired.'})
            amount = Decimal(request.session['cart_price_data']['amount_payable'])  # sum of item final price * qty
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid checkout type.'})

        if amount < coupon.minimum_purchase_amount:
            return JsonResponse({
                'status': 'error', 
                'message': f'Requires minimum purchase of ₹{coupon.minimum_purchase_amount}'
            })

        discount = coupon.calculate_discount(amount)   # amount*(discount /100)
        discounted_amount = (amount - discount).quantize(Decimal('0.01'))
        discount_percent=coupon.discount_percentage

        request.session['applied_coupon'] = {
            'coupon_code': coupon.coupon_code,
            'coupon_discount': str(discount),
            'final_amount': str(discounted_amount),
            'discount_percent':discount_percent,
            'coupon_applied': True,
            'checkout_type':checkout_type
        }

        return JsonResponse({
            'status': 'success',
            'message': f'{code} applied successfully.',
            'discount': str(discount), 
            'final_amount': str(discounted_amount),
        })
@login_required
@never_cache
def remove_coupon(request):
    if request.method == 'POST':
        request.session.pop('applied_coupon', None)
        checkout_type = request.POST.get('checkout_type') 

        
        if checkout_type == 'buy_now':
            final_amount = request.session['buy_now_order_data']['total_price']  # item final price * qty
        else:
            final_amount = request.session['cart_price_data']['amount_payable']   # sum of item final price * qty

        return JsonResponse({
            'status': 'success',
            'message': 'Coupon removed.',
            'final_amount': str(final_amount),
            'discount': '0.00'
        })



@never_cache
@login_required(login_url='login')
def payment_method(request):
    if 'order_data' not in request.session:
        messages.error(request, "No order data found. Please start over.")
        return redirect('product_listing')
    
    order_data = request.session['order_data']
    is_cart_checkout = order_data.get('is_cart_checkout', False)
    address = get_object_or_404(UserAddress,id=order_data['address_id'],user=request.user)
    total_amount = Decimal(order_data.get('total_amount','0'))       # Sum of all distributed item prices
    applied_coupon=request.session.get('applied_coupon')

    ordering_items = order_data.get('cart_items',[])

    variants = []
    
    
    for item in ordering_items:
        variant = get_object_or_404(ProductVariant, id=item['variant_id'])
        quantity = int(item['quantity'])
        price = Decimal(item['unit_price'])    # Item distributed price per qty
        item_total = Decimal(item.get('line_total',quantity * price))  # Item distributed * qty

        variants.append({
            'variant':variant, 'quantity':quantity,
            'price':price,'item_total':item_total,
        })

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'COD')

        if payment_method in ['COD', 'WALLET']:
            try:
                with transaction.atomic():
                
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

                    order = Order.objects.create(
                        user=request.user,
                        address=address,
                        total_amount=total_amount,
                        payment_method=payment_method,
                        is_paid=(payment_method == 'WALLET')
                    )
                    
                    for item in variants:
                        for _ in range(item['quantity']):
                            OrderItem.objects.create(
                                order=order,
                                variant=item['variant'],
                                quantity=1, 
                                price=item['price'], 
                                status='ACTIVE',
                                delivery_status='PENDING'
                            )
                       
                        item['variant'].stock -= item['quantity']
                        item['variant'].save()


                    if is_cart_checkout:
                        CartProducts.objects.filter(user=request.user).delete()


                    del request.session['order_data']
                    return redirect('order_success', order_id=order.id)

            except Exception as e:
                messages.error(request, f"Error processing order: {str(e)}")
                return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=variants[0]['variant'].id)

        elif payment_method == 'RAZORPAY':
            currency = 'INR'
            amount = int(total_amount * 100)  #  paise convert

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create(dict(amount=amount, currency=currency, payment_capture='1'))
            razorpay_order_id = razorpay_order['id']
            
            context = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                'razorpay_amount': amount,
                'currency': currency,
                'callback_url': request.build_absolute_uri(reverse('razorpay_success')),
            }
            return render(request, 'user/razorpay_checkout.html', context)

    return render(request, 'user/payment_method.html', {
        'variants': variants,
        'total_amount': total_amount,
        'address': address,
        'is_cart_checkout': is_cart_checkout
    })



@csrf_exempt
def razorpay_success(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            
            try:
                client.utility.verify_payment_signature(params_dict)
            except:
                return redirect('order_error')
            
            
            if 'order_data' not in request.session:
                return redirect('order_error')
                
            order_data = request.session['order_data']
            is_cart_checkout = order_data.get('is_cart_checkout', False)
            address = get_object_or_404(UserAddress, id=order_data['address_id'], user=request.user)
            total_amount = Decimal(order_data.get('total_amount', '0'))
            
            ordering_items = order_data.get('cart_items', [])
            variants = []
            for item in ordering_items:
                variant = get_object_or_404(ProductVariant, id=item['variant_id'])
                quantity = int(item['quantity'])
                price = Decimal(item['unit_price'])
                item_total = Decimal(item.get('line_total', quantity * price))
                variants.append({
                    'variant': variant, 'quantity': quantity,
                    'price': price, 'item_total': item_total,
                })

            with transaction.atomic():
                for item in variants:
                    if item['variant'].stock < item['quantity']:
                        messages.error(request, f"Insufficient stock for {item['variant']}.")
                        return redirect('cart_checkout' if is_cart_checkout else 'buy_now', variant_id=item['variant'].id)
                
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

                for item in variants:
                    for _ in range(item['quantity']):
                        OrderItem.objects.create(
                            order=order,
                            variant=item['variant'],
                            quantity=1, 
                            price=item['price'], 
                            status='ACTIVE',
                            delivery_status='PENDING'
                        )
                
                    item['variant'].stock -= item['quantity']
                    item['variant'].save()
                
                if is_cart_checkout:
                    CartProducts.objects.filter(user=request.user).delete()

                del request.session['order_data']
                return redirect('order_success', order_id=order.id)
                
        except Exception as e:
            print(f"Razorpay Error: {e}") 
            return redirect('order_error')
            
    return redirect('order_error')


@never_cache
@login_required(login_url='login')
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    same_items ={}
    for item in order.items.all():
        varid= item.variant.id
        if varid not in same_items:
            same_items[varid] = {
                'variant': item.variant,
                'quantity': 0,
                'unit_price': item.price,
                'image': item.variant.product.product_image.first(),
            }
        same_items[varid]['quantity'] += 1
    same_items = list(same_items.values())
    print(same_items)

    total_mrp = Decimal('0.00')
    for item in order.items.all():
        # Ideally we should have stored original MRP in OrderItem, but using current variant price as fallback/proxy
        # The user wants "how much discount he got", so we compare Paid Price vs Current MRP (or stored if we had it)
        # Using variant.price (Current MRP)
        total_mrp += item.variant.price * item.quantity

    total_savings = total_mrp - order.total_amount

    context = {
        'order': order,
        'same_items':same_items,
        'total_mrp': total_mrp,
        'total_savings': total_savings,
    }
    return render(request, 'user/order_success.html', context)

@login_required(login_url='login')
def order_error(request):
    
    context = {
        'order': None,
    }
    return render(request, 'user/order_error.html', context)

from django.http import HttpResponse

@login_required
def download_invoice_pdf(request,order_id):

    order= get_object_or_404(Order,id=order_id,user=request.user)

    order_items= OrderItem.objects.filter(order=order)
    
    
    grouped_items = {}
    for item in order_items:
        var_id = item.variant.id
        if var_id not in grouped_items:
            grouped_items[var_id] = {
                'variant': item.variant,
                'quantity': 0,
                'unit_price': item.price,
                'total_price': Decimal('0.00')
            }
        grouped_items[var_id]['quantity'] += item.quantity
        
        grouped_items[var_id]['total_price'] += (item.price * item.quantity)

    # Calculate totals for invoice
    total_mrp = Decimal('0.00')
    for item in order_items:
         total_mrp += item.variant.price * item.quantity
    
    total_savings = total_mrp - order.total_amount
    
    # Enrich grouped_items with specific discount info per item group if needed, 
    # but the invoice template usually iterates nicely. 
    # Let's just pass the totals and let the template calculation display per-row if needed.
    # Actually, for the table rows, we might want 'unit_mrp' which is item.variant.price
    for val in grouped_items.values():
        val['unit_mrp'] = val['variant'].price
        val['total_mrp'] = val['variant'].price * val['quantity']
        val['savings'] = val['total_mrp'] - val['total_price']

    data = {
        'order': order,
        'order_items': list(grouped_items.values()),
        'customer_name': request.user.get_full_name() or request.user.username,
        'total_mrp': total_mrp,
        'total_savings': total_savings,
    }
    pdf= render_to_pdf('user/invoice_pdf.html', data)

    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_Order_{order.id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse('Not Found',status=404)

@login_required(login_url='login')
def orderlist(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip() 
    
    if query:
        
        items = OrderItem.objects.filter(
            order__user=request.user
        ).filter(
            Q(variant__variant_name__icontains=query) |
            Q(variant__product__name__icontains=query) |
            Q(variant__product__brand__icontains=query) |
            Q(variant__product__category__name__icontains=query)
        )
        
        
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
                
                item.variant.stock += item.quantity
                item.variant.save()

                item_total = item.quantity * item.price
                actual_order_total= sum(it.price * it.quantity for it in order.items.all()) # BEFORE COUPON APPLIED
                paid_order_total= order.total_amount  # AFTER ANY COUPON APPLIED
            # PAID AMOUNT OF EACH ITEM IF COUPON IS APPLIED
                refund_amount= (item_total/actual_order_total)* paid_order_total if actual_order_total > 0 else 0
                refund_amount = Decimal(refund_amount).quantize(Decimal("0.01"))

                order.total_amount = max(0, order.total_amount - refund_amount)

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
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    
    if item.delivery_status != 'DELIVERED':
        messages.error(request, "This item cannot be returned as it has not been delivered.")
        return redirect('order_details', order_id=order.id,item_id=item.id)

    
    if request.method == 'POST':
        reason=request.POST.get('reason')
        other_reason= request.POST.get('other_reason')
        try:
            with transaction.atomic():
            
                if ReturnRequest.objects.filter(order_item=item).exists():
                    messages.warning(request,'The return request for the same product is already made.')
                    return redirect('order_details', order_id=order.id, item_id=item.id)
                
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