# models.py
from django.db import models

class Product(models.Model):
    PRODUCT_TYPES = (
        ('None', 'None'),
        ('lactate', 'Lactate'),
        ('carne', 'Carne'),
        ('legume', 'Legume'),
        ('fructe', 'Fructe'),
        # Add more choices as needed
    )

    product_name = models.CharField(max_length=100)
    brands = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    categories = models.CharField(max_length=200)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return self.product_name


class ApiProduct(models.Model):
    PRODUCT_TYPES = (
        ('None', 'None'),
        ('lactate', 'Lactate'),
        ('carne', 'Carne'),
        ('legume', 'Legume'),
        ('fructe', 'Fructe'),
        # Add more choices as needed
    )
    
    product_name = models.CharField(max_length=100)
    brands = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    categories = models.CharField(max_length=200)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return self.product_name
