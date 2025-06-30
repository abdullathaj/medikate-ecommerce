from django.contrib import admin
from .models import Categories,Product,Product_Varients,ProductImage

# Register your models here.
admin.site.register(Categories)
admin.site.register(Product_Varients)
admin.site.register(Product)
admin.site.register(ProductImage)

