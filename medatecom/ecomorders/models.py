from django.db import models
from ecomproducts.models import Categories,Product,ProductVariant,ProductImage
from ecomusers.models import User,UserAddress,CartProducts
from datetime import timedelta
from django.utils import timezone



# Create your models here.
class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    PAYMENT_CHOICES=[
        ('COD','Cash on Delivery'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(UserAddress, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='COD')  # Always 'COD' for now
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    @property
    def expected_delivery_date(self):
        """Calculate expected delivery date as 7 days from creation."""
        return self.created_at + timedelta(days=7)


class OrderItem(models.Model):

    STATUS_CHOICES=[
        ('ACTIVE','Active'),
        ('CANCELLED','Cancelled'),
    ]
    DELIVERY_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('ARRIVED', 'Arrived'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at the time of order
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    delivery_status=models.CharField(max_length=20, choices= DELIVERY_STATUS_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.price

    @property
    def display_status(self):
        if self.order.status=='CANCELLED' or self.status=='CANCELLED':
            return 'Cancelled'
        
        if self.delivery_status:
            return self.delivery_status
        
        
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
