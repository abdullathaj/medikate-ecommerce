from django.db import models

# Create your models here.
class Categories(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=150)
    description=models.TextField(blank=True)

    
    def __str__(self):
        return self.name
    
class Product_Varients(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product_varient')
    varient_name=models.CharField(max_length=200)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.PositiveIntegerField(default=0)
    size=models.CharField(max_length=50,blank=True,null=True)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return f'{self.product.name} {self.varient_name}'

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='product')
    image=models.ImageField(upload_to='admin/images')

    def __str__(self):
        return f'Image for {self.product.name}'


