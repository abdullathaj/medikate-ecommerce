from django import forms
from django.forms import ModelForm,inlineformset_factory
from ecomusers.models import User
from ecomproducts.models import Categories,Product,Product_Varients,ProductImage
from django.contrib.auth.forms import UserCreationForm

# FORM FOR CREATION OF NEW USER
class Useraddform(UserCreationForm):
    email=forms.EmailField(required=True)
    class Meta:
        model=User
        fields=['username','email','first_name','is_superuser','is_active','password1','password2']

# FORM FOR ADDING NEW CATEGORY

class CategoryAddForm(ModelForm):
    class Meta:
        model = Categories
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductAddForm(ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category','description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product description',
                'rows': 4
            }),
        }
class VarientAddForm(ModelForm):
    class Meta:
        model = Product_Varients
        fields = ['varient_name', 'price', 'stock', 'size', 'is_active']
        widgets = {
            'varient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter variant name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter price'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
            'size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter size (optional)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
class ProductImageForm(ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


VarientFormset=inlineformset_factory(Product,Product_Varients,form=VarientAddForm,extra=1,can_delete=False)
ImageFormset=inlineformset_factory(Product,ProductImage,form=ProductImageForm,
                                    extra=3,can_delete=False,max_num=3,min_num=3,
                                    validate_min=True,validate_max=True)