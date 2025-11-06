from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User,UserAddress
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
import re

class UserProfileForm(UserChangeForm):
      
    password=None
    class Meta:
        model=User
        fields=['username','first_name','last_name','phone']
        widgets={
            'username':forms.TextInput(attrs={'class':'form-control'}),
            'first_name':forms.TextInput(attrs={'class':'form-control'}),
            'last_name':forms.TextInput(attrs={'class':'form-control'}),
            'phone':forms.TextInput(attrs={'class':'form-control'}),

        }
    def clean(self):
        cleaned_data= super().clean()
        username= cleaned_data.get('username')
        first_name,last_name= cleaned_data.get('first_name'),cleaned_data.get('last_name')
        phone= cleaned_data.get('phone')

        if username and not re.match(r'^[a-zA-Z0-9_]+$', username):
            self.add_error('username', 'Username should only contain letters, digits, and underscores.')

        if first_name and not re.match(r'^[A-Za-z]+$', first_name):
            self.add_error('first_name', 'First name should only contain letters.')

        if last_name and not re.match(r'^[A-Za-z]+$', last_name):
            self.add_error('last_name', 'Last name should only contain letters.')

        if phone and not re.match(r'^\d{10}$', phone):
            self.add_error('phone', 'Phone number must be a valid 10-digit number.')
        
        return cleaned_data



class EmailChangeForm(forms.Form):

    new_email=forms.EmailField(
        label="New Email",
        widget=forms.EmailInput(attrs={'class':'form-control'}),
        max_length=100
    )

    def clean_new_email(self):
        new_email=self.cleaned_data['new_email']
        if User.objects.filter(email=new_email).exists():
            raise forms.ValidationError('This email is already exists.')
        return new_email


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

        if addressline_1 and not re.match(r'^[A-Za-z0-9 ]+$',addressline_1):
            self.add_error('addressline_1','Address should not contain symbols')
        if addressline_2 and not re.match(r'^[A-Za-z0-9 ]+$',addressline_2):
            self.add_error('addressline_2','Address should not contain symbols')
        if city and not re.match(r'^[A-Za-z ]+$',city):
            self.add_error('city','City name must only contain letters.')
        if state and not re.match(r'^[A-Za-z ]+$',state):
            self.add_error('state','State name must only contain letters.')
        if nation and not re.match(r'^[A-Za-z]+$',nation):
            self.add_error('nation','Nation name must only contain letters.')
        if postal_code and not re.match(r'^\d{6}$',postal_code):
            self.add_error('postal_code','Postal code must contain 6 digits only.')

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


class UserPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not check_password(old_password, self.user.password):
            raise forms.ValidationError("Current password is incorrect.")
        return old_password

    def clean_new_password2(self):
        new_password1 = self.cleaned_data.get("new_password1")
        new_password2 = self.cleaned_data.get("new_password2")
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("The new passwords do not match.")
        if new_password1:
            password_validation.validate_password(new_password2, self.user)
        return new_password2

    def save(self):
        new_password = self.cleaned_data["new_password1"]
        self.user.set_password(new_password)
        self.user.save()
        return self.user