from django import forms
from django.forms import ModelForm,inlineformset_factory,BaseInlineFormSet
from ecomusers.models import User
from ecomproducts.models import Categories,Product,ProductVariant,ProductImage,Offer,Coupon
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re


# FORM FOR CREATION OF NEW USER
class Useraddform(UserCreationForm):
    email=forms.EmailField(required=True)
    class Meta:
        model=User
        fields=['username','email','first_name','is_superuser','is_active','password1','password2']

# FORM FOR ADDING NEW CATEGORY

class CategoryAddForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Categories.objects.filter(name__iexact=name).exists():
            raise ValidationError("The category with the same name already exists.")
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9\s]*', name):
            raise ValidationError("Category name should only contain letters, digits, and spaces.")
        return name

class ProductAddForm(ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category','description','brand']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'brand': forms.TextInput(attrs={'class':'form-control','placeholder':'Enter the brand (Optional)'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product description',
                'rows': 4
            }),
        }
    def __init__(self,*args,**kwargs):
         super(ProductAddForm,self).__init__(*args,**kwargs)
         self.fields['category'].empty_label='Select from categories'

    def clean_name(self):
            ''' Product name will not allow other symbols and Reject duplicate names Case Insestive way.'''
            name = self.cleaned_data.get('name')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9\s]*', name):
                raise ValidationError("Product name should only contain letters,digits and spaces.")  
            # FOR UNIQUE PRODUCT - CASE INSENSITIVE
            qs = Product.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("A product with this name already exists.")
            return name
    
    def clean_brand(self):
        ''' Brand name do not allows any other symbols.'''
        brand= self.cleaned_data.get('brand')
        if brand and not re.fullmatch(r'[a-zA-Z0-9\s]*',brand):
            raise ValidationError('Brand name should only contain Alphabets,Digits and Spaces.')
        return brand

class VariantAddForm(ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['variant_name', 'price', 'stock', 'size', ]
        widgets = {
            'variant_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter variant name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter price'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
            'size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter size (optional)'}),
            # 'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
 
    def clean_variant_name(self):
        name = self.cleaned_data['variant_name']
        if not re.fullmatch(r'[A-Za-z0-9\s]+', name):
            raise ValidationError("Variant name should contain only letters, digits and spaces.")
        return name


    def clean_price(self):
            price = self.cleaned_data['price']
            if price <= 0:
                raise ValidationError("Price must be a positive number.")
            return price

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise ValidationError("Stock cannot be negative.")
        return stock


class ProductImageForm(ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class BaseVariantFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if form.cleaned_data.get('DELETE', False):
                continue
            name = form.cleaned_data.get('variant_name')
            if name in seen:
                raise ValidationError(f"Duplicate variant name: '{name}'")
            seen.add(name)

VariantFormset=inlineformset_factory(Product,ProductVariant,form=VariantAddForm,formset=BaseVariantFormset,
                                     extra=0, min_num=1,validate_min=True)
ImageFormset=inlineformset_factory(Product,ProductImage,form=ProductImageForm,
                                    extra=0,max_num=3,min_num=3,
                                    validate_min=True,validate_max=True)

class OfferForm(forms.ModelForm):
    class Meta:
        model= Offer
        fields= ['name','description','valid_from','valid_to',
                 'discount_percentage','category','product']
        
        widgets={
            'name':forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data= super().clean()
        category= cleaned_data.get('category')
        product= cleaned_data.get('product')
        name= cleaned_data.get('name')
        
        if name and not re.match(r'^[a-zA-Z0-9]+$',name):
            raise ValidationError('The offer name must only contain letters and digits.')
        elif product and Offer.objects.filter(product=product).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This product already has an existing offer. Cannot create this offer.')
        elif category and Offer.objects.filter(category=category).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This category already has an existing offer. Cannot create the offer.')
        elif category and product:
            raise ValidationError('Offer can only apply either Product or Category, not for both.')
        elif not category and not product:
            raise ValidationError('Must select Either product or category.')
        return cleaned_data
        
class OfferEditForm(forms.ModelForm):
    class Meta:
        model= Offer
        fields= ['description','valid_from','valid_to','discount_percentage','is_active']

        widgets= {
            'description': forms.Textarea(attrs={'rows': 3, 'class':'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'type':'datetime-local', 'class':'form-control'}),
            'valid_to': forms.DateTimeInput(attrs={'type':'datetime-local', 'class':'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class':'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'})
        }

class CouponForm(forms.ModelForm):
    class Meta:
        model= Coupon
        fields=[
            'coupon_code','description','valid_from','valid_to',
            'discount_percentage','minimum_purchase_amount','max_usage_limit'
        ]

        widgets= {
            'coupon_code': forms.TextInput(attrs={'class':'form-control'}),
            'description' : forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'valid_from' : forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'valid_to' : forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'discount_percentage' : forms.NumberInput(attrs={'class':'form-control'}),
            'minimum_purchase_amount': forms.NumberInput(attrs={'class':'form-control'}),
            'max_usage_limit': forms.NumberInput(attrs={'class':'form-control'}),
            # 'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
    def clean_coupon_code(self):
        code= self.cleaned_data.get('coupon_code')
        if not re.match(r'^[a-zA-Z0-9]+$',code):
            raise ValidationError('Coupon code only contain letters and digits.')
        return code

class CouponEditForm(forms.ModelForm):
    class Meta:
        model= Coupon
        fields=['description','discount_percentage','valid_from','valid_to',
                'minimum_purchase_amount','max_usage_limit','is_active'
                ]
        widgets={
            'description':forms.Textarea(attrs={'rows':3,'class':'form-control'}),
            'discount_percentage':forms.NumberInput(attrs={'class':'form-control'}),           
            'valid_from':forms.DateTimeInput(attrs={'type':'datetime-local','class':'form-control'}),
            'valid_to':forms.DateTimeInput(attrs={'type':'datetime-local','class':'form-control'}),
            'minimum_purchase_amount':forms.NumberInput(attrs={'class':'form-control'}),
            'max_usage_limit':forms.NumberInput(attrs={'class':'form-control'}),
            'is_active':forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

