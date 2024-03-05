# Generated by Django 5.0.2 on 2024-03-05 20:10

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0017_user_activity_level_user_age_user_goal_user_height_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='activity_level',
        ),
        migrations.RemoveField(
            model_name='user',
            name='age',
        ),
        migrations.RemoveField(
            model_name='user',
            name='goal',
        ),
        migrations.RemoveField(
            model_name='user',
            name='height',
        ),
        migrations.RemoveField(
            model_name='user',
            name='weight',
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('age', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('weight', models.DecimalField(decimal_places=2, max_digits=5)),
                ('activity_level', models.CharField(choices=[('sedentary', 'Sedentary'), ('lightly_active', 'Lightly Active'), ('moderately_active', 'Moderately Active'), ('very_active', 'Very Active'), ('extra_active', 'Extra Active')], default='sedentary', max_length=20)),
                ('goal', models.CharField(choices=[('cut', 'Cut'), ('bulk', 'Bulk'), ('maintain', 'Maintain')], default='maintain', max_length=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
