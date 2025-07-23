from django.db import models
from django.db.models.functions import Lower
from decimal import Decimal,ROUND_HALF_UP
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
    
class ProductVarients(models.Model):

    class Meta:
        unique_together=('product','varient_name')

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
        return self.price + self.price * Decimal('0.2').quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)

class ProductImage(models.Model): # related_name SHOULD HAVE TO CHANGE TO product_image
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_image')
    image=models.ImageField(upload_to='admin/images')

    def __str__(self):
        return f'Image for {self.product.name}'


