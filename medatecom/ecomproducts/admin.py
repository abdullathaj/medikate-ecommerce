from django.contrib import admin
from .models import Categories,Product,ProductVariant,ProductImage,Coupon,Offer

# Register your models here.
admin.site.register(Categories)
admin.site.register(ProductVariant)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Coupon)
admin.site.register(Offer)


