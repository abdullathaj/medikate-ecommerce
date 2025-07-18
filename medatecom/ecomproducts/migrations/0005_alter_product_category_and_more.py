# Generated by Django 5.2.1 on 2025-06-27 04:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecomproducts', '0004_product_product_varients'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='ecomproducts.categories'),
        ),
        migrations.AlterField(
            model_name='product_varients',
            name='varient_name',
            field=models.CharField(max_length=200),
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product', to='ecomproducts.product')),
            ],
        ),
    ]
