# Generated by Django 5.0.2 on 2024-02-19 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WellnessCorner', '0003_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='Allergy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddField(
            model_name='user',
            name='allergies',
            field=models.ManyToManyField(blank=True, to='WellnessCorner.allergy'),
        ),
    ]