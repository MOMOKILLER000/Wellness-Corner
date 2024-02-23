# Generated by Django 5.0.2 on 2024-02-23 19:56

import WellnessCorner.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Allergy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='ApiProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=100)),
                ('brands', models.CharField(max_length=100)),
                ('quantity', models.CharField(max_length=50)),
                ('categories', models.CharField(max_length=200)),
                ('image', models.ImageField(blank=True, null=True, upload_to='api_product_images/')),
                ('protein_per_100g', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True)),
                ('carbs_per_100g', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True)),
                ('fats_per_100g', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True)),
                ('kcal_per_100g', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('product_type', models.CharField(choices=[('None', 'None'), ('lactate', 'Lactate'), ('carne', 'Carne'), ('legume', 'Legume'), ('fructe', 'Fructe')], default='None', max_length=20)),
                ('user_rating', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('allergies', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Basket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='PendingProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=100)),
                ('brands', models.CharField(max_length=100)),
                ('quantity', models.CharField(max_length=50)),
                ('categories', models.CharField(max_length=200)),
                ('image', models.ImageField(blank=True, null=True, upload_to='pending_product_images/')),
                ('protein_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('carbs_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('fats_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kcal_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('product_type', models.CharField(choices=[('None', 'None'), ('lactate', 'Lactate'), ('carne', 'Carne'), ('legume', 'Legume'), ('fructe', 'Fructe')], default='None', max_length=20)),
                ('user_rating', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('allergies', models.TextField(blank=True, null=True)),
                ('approved', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=100)),
                ('brands', models.CharField(max_length=100)),
                ('quantity', models.CharField(max_length=50)),
                ('categories', models.CharField(max_length=200)),
                ('image', models.ImageField(blank=True, null=True, upload_to='product_images/')),
                ('protein_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('carbs_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('fats_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kcal_per_100g', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('product_type', models.CharField(choices=[('None', 'None'), ('lactate', 'Lactate'), ('carne', 'Carne'), ('legume', 'Legume'), ('fructe', 'Fructe')], default='None', max_length=20)),
                ('user_rating', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('allergies', models.TextField(blank=True, null=True)),
                ('approved', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='BasketItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('database', 'Database'), ('api', 'API')], max_length=20)),
                ('api_product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='WellnessCorner.apiproduct')),
                ('basket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='WellnessCorner.basket')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='WellnessCorner.product')),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('email', models.EmailField(default='', max_length=254, unique=True)),
                ('name', models.CharField(default='', max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('is_superuser', models.BooleanField(default=False)),
                ('is_staff', models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('is_client', models.BooleanField(default=False, help_text='Check this box if you are a client.')),
                ('allergies', models.ManyToManyField(blank=True, to='WellnessCorner.allergy')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
            managers=[
                ('objects', WellnessCorner.models.CustomUserManager()),
            ],
        ),
        migrations.AddField(
            model_name='basket',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
