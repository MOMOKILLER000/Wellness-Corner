# Generated by Django 5.0.2 on 2024-03-09 20:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0032_product_saturated_fats_per_100g_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='nutriscore',
            field=models.CharField(blank=True, max_length=1, null=True),
        ),
    ]
