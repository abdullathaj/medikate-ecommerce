from django.contrib import admin

from .models import User,UserAddress,WishlistProducts,CartProducts,Wallet

# Register your models here.

admin.site.register(User)
admin.site.register(UserAddress)
admin.site.register(WishlistProducts)
admin.site.register(CartProducts)
admin.site.register(Wallet)