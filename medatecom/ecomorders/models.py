from django.db import models
from ecomproducts.models import Categories,Product,ProductVariant,ProductImage
from ecomusers.models import User,UserAddress,CartProducts
from datetime import timedelta
from django.utils import timezone


# Create your models here.
class Order(models.Model):
    
    PAYMENT_CHOICES=[
        ('COD','Cash on Delivery'),
        ('RAZORPAY','Razorpay'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(UserAddress, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='COD')  # Always 'COD' for now
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_paid = models.BooleanField(default=False)
    razorpay_order_id= models.CharField(max_length=255, null= True, blank= True)
    razorpay_payment_id= models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature= models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    @property
    def expected_delivery_date(self):
        """Calculate expected delivery date as 7 days from creation."""
        return self.created_at + timedelta(days=7)
    @property
    def overall_status(self):
        """Summarize order status based on item statuses."""
        item_statuses = list(self.items.values_list("delivery_status", flat=True))

        if all(status == 'CANCELLED' for status in item_statuses):
            return 'Cancelled'
        if all(status == 'DELIVERED' for status in item_statuses):
            return 'Delivered'
        if any(status == 'SHIPPED' for status in item_statuses):
            return 'Shipped'
        if any(status == 'PROCESSING' for status in item_statuses):
            return 'Processing'
        if any(status == 'PENDING' for status in item_statuses):
            return 'Pending'
        return 'Pending'

class OrderItem(models.Model):
    
    STATUS_CHOICES=[
        ('ACTIVE','Active'),
        ('CANCELLED','Cancelled'),
        ('RETURNED','Returned'),
    ]

    DELIVERY_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('ARRIVED', 'Arrived'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED','Returned'),
    ]

    CANCELLATION_REASON_CHOICES = [
        ('DELAY', 'Delivery taking too long'),
        ('CHANGED_MIND', 'Changed my mind'),
        ('FOUND_BETTER', 'Found a better price elsewhere'),
        ('WRONG_ITEM', 'Ordered wrong item'),
        ('OTHER', 'Other reason'),
    ]

    RETURN_REASON_CHOICES = [
        ('DAMAGED', 'Product was damaged'),
        ('DEFECTIVE', 'Product was defective'),
        ('WRONG_ITEM', 'Wrong item delivered'),
        ('NOT_SATISFIED', 'Not satisfied with the product'),
        ('OTHER', 'Other reason'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items',null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, null=True, decimal_places=2)  # price at the time of order
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    delivery_status=models.CharField(max_length=20, choices= DELIVERY_STATUS_CHOICES, blank=True, null=True)
    # Regarding with item cancellation.
    cancellation_reason=models.CharField(max_length=50, choices= CANCELLATION_REASON_CHOICES, blank=True, null=True)
    other_reason= models.TextField(blank=True, null=True) # If the user selected other reasons.

    # REGARDING WITH ITEM RETURNING
    return_reason= models.CharField(max_length=50, choices=RETURN_REASON_CHOICES, blank=True, null=True)
    return_other_reason=models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.price

    @property
    def display_status(self):
        if self.order.overall_status=='CANCELLED' or self.status=='CANCELLED':
            return 'Cancelled'
        
        if self.status == 'RETURNED':
            return 'Returned'
        
        if self.delivery_status:
            return dict(self.DELIVERY_STATUS_CHOICES).get(self.delivery_status,self.delivery_status)
        
        
        order_date=self.order.created_at.date()
        today=timezone.now().date()
        days_passed=(today-order_date).days

        if days_passed==0:
            return 'Pending'
        elif days_passed==1:
            return 'Processing'
        elif days_passed >= 2 and days_passed <= 4:
            return 'Shipped'
        elif days_passed ==5 and days_passed<=7:
            return 'Arrived'
        elif days_passed>=7:
            return 'Delivered'
        else:
            return 'Processing'
