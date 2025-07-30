from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User,UserAddress

class UserProfileForm(UserChangeForm):
    
    password=None
    class Meta:
        model=User
        fields=['username','first_name','last_name','email','phone']
        widgets={
            'username':forms.TextInput(attrs={'class':'form-control'}),
            'first_name':forms.TextInput(attrs={'class':'form-control'}),
            'last_name':forms.TextInput(attrs={'class':'form-control'}),
            'phone':forms.TextInput(attrs={'class':'form-control'}),
            'email':forms.EmailInput(attrs={'class':'form-control'})

        }

class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = ['addressline_1', 'addressline_2', 'city', 'state', 'nation', 'postal_code', 'is_default']
        widgets = {
            'addressline_1': forms.TextInput(attrs={'class': 'form-control'}),
            'addressline_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'nation': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        user = self.instance.user if self.instance.pk else self.initial.get('user')
        if user and UserAddress.objects.filter(user=user).count() >= 5 and not self.instance.pk:
            raise forms.ValidationError("You can only add up to 5 addresses.")
