# Generated by Django 5.0.2 on 2024-03-09 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0033_alter_product_nutriscore'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingproduct',
            name='saturated_fats_per_100g',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='pendingproduct',
            name='sodium_per_100g',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='pendingproduct',
            name='sugars_per_100g',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]