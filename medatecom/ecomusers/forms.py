from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User,UserAddress
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import check_password

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