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
        user = self.initial.get('user') or self.instance.user  # get user from form

        addressline_1 = cleaned_data.get('addressline_1')
        addressline_2 = cleaned_data.get('addressline_2')
        city = cleaned_data.get('city')
        state = cleaned_data.get('state')
        nation = cleaned_data.get('nation')
        postal_code = cleaned_data.get('postal_code')

        # Check for duplicates
        if user and addressline_1 and city and state and nation and postal_code:
            exists = UserAddress.objects.filter(
                user=user,
                addressline_1=addressline_1,
                addressline_2=addressline_2,
                city=city,
                state=state,
                nation=nation,
                postal_code=postal_code
            )
            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise forms.ValidationError("This address already exists for you.")

        # Limit to 5 addresses
        if user and UserAddress.objects.filter(user=user).count() >= 5 and not self.instance.pk:
            raise forms.ValidationError("You can only add up to 5 addresses.")

        return cleaned_data
