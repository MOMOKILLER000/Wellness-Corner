# Generated by Django 5.0.2 on 2024-02-21 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0004_alter_product_product_name_pendingproduct_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pendingproduct',
            name='created_at',
        ),
        migrations.AlterField(
            model_name='pendingproduct',
            name='product_type',
            field=models.CharField(choices=[('None', 'None'), ('lactate', 'Lactate'), ('carne', 'Carne'), ('legume', 'Legume'), ('fructe', 'Fructe')], default='None', max_length=20),
        ),
    ]