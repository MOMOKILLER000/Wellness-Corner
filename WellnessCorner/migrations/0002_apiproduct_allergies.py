# Generated by Django 5.0.2 on 2024-02-19 13:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiproduct',
            name='allergies',
            field=models.TextField(blank=True, null=True),
        ),
    ]
