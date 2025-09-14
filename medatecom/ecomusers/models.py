from django.db import models
from django.contrib.auth.models import AbstractUser
from ecomproducts.models import Product,ProductVariant,ProductImage,Categories
from django.core.exceptions import ValidationError


class User(AbstractUser):
    email = models.EmailField(max_length=100,unique=True)
    phone = models.CharField(max_length=15,null=True,blank=True)
    is_superuser=models.BooleanField(default=False)

    

    def __str__(self):
        return self.username

# CREATING DELIVERY ADDRESSES FOR USER

class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    addressline_1 = models.CharField(max_length=100)
    addressline_2 = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    nation = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=['user', 'addressline_1', 'addressline_2', 'city', 'state', 'nation', 'postal_code'],
    #             name='unique_address_per_user'
    #         )
    #     ]

    def clean(self):
        if self.user.addresses.count() >= 5 and not self.pk:
            raise ValidationError("Maximum 5 addresses allowed per user.")

    def save(self, *args, **kwargs):
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.addressline_1},{self.addressline_2}, {self.city},{self.state}, {self.nation},{self.postal_code}.'


# # MODEL FOR USERS WISHLIST
class WishlistProducts(models.Model):
    class Meta:
        unique_together=('user','variant')

    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='wishlist')
    variant=models.ForeignKey(ProductVariant,on_delete=models.CASCADE,related_name='wishist_products')
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist: {self.variant}"

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
    def total_price(self):
        return self.quantity * self.variant.price


# MODEL FOR USER WALLET
class Wallet(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='wallet')
    balance=models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f'{self.user.username}s Wallet; Balance- {self.balance}'



       

    
