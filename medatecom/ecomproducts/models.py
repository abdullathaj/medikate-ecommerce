from django.db import models
from django.db.models.functions import Lower
from decimal import Decimal,ROUND_HALF_UP
from django.core.validators import MinValueValidator,MaxValueValidator
from django.utils.text import slugify
import uuid
from django.utils import timezone
# Create your models here.
class Categories(models.Model):
    name = models.CharField(max_length=25, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):

    class Meta:  # FOR UNIQUE NAMING OF PRODUCTS WITH CASE INSENSITIVE
        constraints = [
        models.UniqueConstraint(Lower('name'), name='unique_product_name_ci')
    ]

    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=50,unique=True)
    description=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    brand=models.CharField(max_length=50,blank=True,null=True)

    
    def __str__(self):
        return self.name
    
class ProductVariant(models.Model):

    class Meta:
        unique_together=('product','variant_name')

    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_variant')
    variant_name=models.CharField(max_length=50)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.PositiveIntegerField(default=0)
    size=models.CharField(max_length=50,blank=True,null=True)
    is_active=models.BooleanField(default=True)
    discount = models.PositiveIntegerField(default=10, editable=False) 


    def __str__(self):
        return f'{self.product.name} {self.variant_name}'
    
    @property
    def original_price(self):
        """Calculate original price based on discount percentage."""
        discount_factor = Decimal(1) - Decimal(self.discount) / Decimal(100)
        if discount_factor <= 0:
            return self.price  # Avoid division by zero or negative logic
        original = self.price / discount_factor
        return original.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class ProductImage(models.Model): # related_name SHOULD HAVE TO CHANGE TO product_image
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_image')
    image=models.ImageField(upload_to='admin/images')

    def __str__(self):
        return f'Image for {self.product.name}'

class Coupon(models.Model):
    coupon_code=models.CharField(max_length=50, unique= True, help_text='Unique code for each coupon')
    is_active=models.BooleanField(default=True, help_text='Whether the coupon is active or not')
    description=models.TextField(blank= True, help_text='Optional description for the coupon')
    created_at=models.DateTimeField(auto_now_add=True, help_text='When the coupon is created')
    valid_from=models.DateTimeField(help_text='Start date of coupon validity')
    valid_to=models.DateTimeField(help_text='End date for coupon validity')
    minimum_purchase_amount=models.DecimalField(max_digits=10, decimal_places=2,
                                                validators=[MinValueValidator(1.00, message='minimum purchase amount must be positive')],
                                                help_text='Minimum amount required to apply this coupon')
    
    discount_percentage=models.PositiveIntegerField(validators=[
            MinValueValidator(10, message='the discount must be greater than 10 percent'),
            MaxValueValidator(80, message='the discount must not exeed 80 percent')
        ], help_text='Discount for this coupon is between 10 and 80')
    max_usage_limit=models.PositiveIntegerField(default=0, help_text='Number of times this coupon can use')
    total_usage=models.PositiveIntegerField(default=0, help_text='Number of times this coupon is used')

    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['coupon_code'], name='unique_coupon_code'),
            models.CheckConstraint(check=models.Q(valid_from__lte= models.F('valid_to')),
                                    name='valid_from_before_valid_to')
        ]
    def __str__(self):
        return self.coupon_code
    
    def save(self, *args, **kwargs):
        """Generate a unique coupon code if not provided."""
        if not self.coupon_code:
            self.coupon_code = slugify(f"COUPON-{uuid.uuid4().hex[:10]}").upper()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if the coupon is valid based on date and usage limits."""
        now=timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_to:
            return False
        if self.max_usage_limit > 0 and self.total_usage >= self.max_usage_limit:
            return False
        return True


