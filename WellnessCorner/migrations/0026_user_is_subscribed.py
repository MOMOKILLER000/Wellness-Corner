# Generated by Django 5.0.2 on 2024-03-09 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0025_remove_basket_total_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_subscribed',
            field=models.BooleanField(default=False),
        ),
    ]
