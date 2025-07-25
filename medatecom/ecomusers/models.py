from django.db import models
from django.contrib.auth.models import AbstractUser
from ecomproducts.models import Product,ProductVariant,ProductImage,Categories

class User(AbstractUser):
    email = models.EmailField(max_length=100,unique=True)
    phone = models.CharField(max_length=15,null=True,blank=True)
    is_superuser=models.BooleanField(default=False)


# MODEL FOR CART PRODUCTS
class CartProducts(models.Model):

    class Meta:
        unique_together=('user','variant')

    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='cart')
    variant=models.ForeignKey(ProductVariant,on_delete=models.CASCADE,related_name='cart_items')
    quantity=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Cart: {self.variant}: Qty: {self.quantity}"
    @property
    def price(self):
        return self.quantity * self.variant.price
    
# MODEL FOR USERS WISHLIST
class WishlistProducts(models.Model):
    class Meta:
        unique_together=('user','variant')

    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='wishlist')
    variant=models.ForeignKey(ProductVariant,on_delete=models.CASCADE,related_name='wishist_products')
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist: {self.variant}"

       

    
