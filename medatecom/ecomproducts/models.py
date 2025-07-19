from django.db import models
from decimal import Decimal
# Create your models here.
class Categories(models.Model):
    name = models.CharField(max_length=25, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=50)
    description=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return self.name
    
class ProductVarients(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_varient')
    varient_name=models.CharField(max_length=50)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.PositiveIntegerField(default=0)
    size=models.CharField(max_length=50,blank=True,null=True)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return f'{self.product.name} {self.varient_name}'
    
    @property
    def original_price(self):
        return self.price + self.price * Decimal('0.2')

class ProductImage(models.Model): # related_name SHOULD HAVE TO CHANGE TO product_image
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_image')
    image=models.ImageField(upload_to='admin/images')

    def __str__(self):
        return f'Image for {self.product.name}'


