from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.utils import timezone

class CustomUserManager(UserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)  

    def _create_user(self, email, password=None, **extra_fields):
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class Allergy(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(default='', unique=True)
    name = models.CharField(max_length=255,  default='')

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    is_client = models.BooleanField(default=False, help_text="Check this box if you are a client.")
    allergies = models.ManyToManyField(Allergy, blank=True)  # ManyToManyField to store allergies

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def get_full_name(self):
        return self.name
    
    def get_short_name(self):
        return self.name or self.email.split('@')[0]

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
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Add price field
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True) 

    # Field for approval status
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.product_name

class PendingProduct(models.Model):
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
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    superuser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return self.product_name

    def approve_and_move_to_product(self):
        # Create a new Product instance based on the PendingProduct instance
        product = Product.objects.create(
            product_name=self.product_name,
            brands=self.brands,
            quantity=self.quantity,
            categories=self.categories,
            protein_per_100g=self.protein_per_100g,
            carbs_per_100g=self.carbs_per_100g,
            fats_per_100g=self.fats_per_100g,
            kcal_per_100g=self.kcal_per_100g,
            price=self.price,
            product_type=self.product_type,
            user_rating=self.user_rating,
            allergies=self.allergies,
            approved=True  # Mark as approved
        )
        return product



# models.py
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
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Add price field
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)  # Field to store allergies as JSON string

    def __str__(self):
        return self.product_name

class Basket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BasketItem(models.Model):
    BASKET_SOURCES = (
        ('database', 'Database'),
        ('api', 'API'),
    )

    basket = models.ForeignKey(Basket, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    api_product = models.ForeignKey(ApiProduct, null=True, blank=True, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, choices=BASKET_SOURCES)

    def __str__(self):
        if self.product:
            return f"Product: {self.product.product_name}"
        elif self.api_product:
            return f"API Product: {self.api_product.product_name}"
        else:
            return "Unknown Product"