# Generated by Django 5.2.1 on 2025-06-27 04:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecomproducts', '0005_alter_product_category_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productimage',
            name='image',
            field=models.ImageField(upload_to='admin/images'),
        ),
    ]
