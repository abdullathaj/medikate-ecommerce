from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(max_length=100,unique=True)
    phone = models.CharField(max_length=15,null=True,blank=True)
    is_superuser=models.BooleanField(default=False)
