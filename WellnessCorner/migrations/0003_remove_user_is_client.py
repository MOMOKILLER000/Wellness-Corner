# Generated by Django 5.0.2 on 2024-02-24 10:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0002_pendingproduct_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='is_client',
        ),
    ]
