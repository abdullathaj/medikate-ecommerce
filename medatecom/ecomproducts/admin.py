from django.contrib import admin
from .models import Categories,Product,ProductVarients,ProductImage

# Register your models here.
admin.site.register(Categories)
admin.site.register(ProductVarients)
admin.site.register(Product)
admin.site.register(ProductImage)

