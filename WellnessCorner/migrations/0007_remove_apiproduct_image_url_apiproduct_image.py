# Generated by Django 5.0.2 on 2024-02-22 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0006_apiproduct_image_url_pendingproduct_image_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apiproduct',
            name='image_url',
        ),
        migrations.AddField(
            model_name='apiproduct',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='api_product_images/'),
        ),
    ]