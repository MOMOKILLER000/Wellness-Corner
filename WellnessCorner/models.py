from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.utils import timezone
from django.db.models import Count
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg
from decimal import Decimal
from django.db.models import Sum, F, FloatField

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
    name = models.CharField(max_length=255,  default='', unique=True)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    allergies = models.ManyToManyField(Allergy, blank=True)
    is_subscribed = models.BooleanField(default=False)
    PREFERRED_DIET_CHOICES = [
        ('None', 'None'),
        ('vegan', 'Vegan'),
        ('Vegetarian', 'Vegetarian'),
        ('Low Fat', 'Low Fat'),
        ('High Protein', 'High Protein'),
        ( 'Keto', 'Keto'),
    ]
    diet = models.CharField(max_length=20, choices=PREFERRED_DIET_CHOICES, default='None')
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

class Banned(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    banned_until = models.DateTimeField(null=True, blank=True)
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.PositiveIntegerField()
    height = models.PositiveIntegerField()  
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES,  default='male')
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('lightly_active', 'Lightly Active'),
        ('moderately_active', 'Moderately Active'),
        ('very_active', 'Very Active'),
        ('extra_active', 'Extra Active'),
    ]
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_LEVEL_CHOICES, default='sedentary')
    
    GOAL_CHOICES = [
        ('cut', 'Cut'),
        ('bulk', 'Bulk'),
        ('maintain', 'Maintain'),
    ]
    goal = models.CharField(max_length=10, choices=GOAL_CHOICES, default='maintain')
    daily_calories = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

class Product(models.Model):
    PRODUCT_TYPES = (
        ('None', 'None'),
        ('lactate', 'Lactate'),
        ('carne', 'Carne'),
        ('legume', 'Legume'),
        ('fructe', 'Fructe'),
        
    )

    product_name = models.CharField(max_length=100)
    brands = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    categories = models.CharField(max_length=200)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    ean_code = models.CharField(max_length=13, unique=True, blank=True, null=True, help_text='European Article Number (EAN) code')
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sugars_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    sodium_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    saturated_fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    total_ratings = models.IntegerField(default=0)
    rated_by = models.ManyToManyField(User, through='ProductRating')
    allergies = models.TextField(null=True, blank=True) 
    nutriscore = models.CharField(max_length=1, null=True, blank=True)
    approved = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    def __str__(self):
        return self.product_name
    
    def calculate_average_rating(self):
        
        average_rating = self.productrating_set.aggregate(avg_rating=Avg('rating'))['avg_rating']
        if average_rating is not None:
            self.user_rating = average_rating
            self.save()

    def calculate_nutriscore(self):
        thresholds = {
            'energy': 170,  
            'saturated_fats': 1.5,  
            'sugars': 5,  
            'sodium': 90,  
        }

        score = 0

        
        if self.kcal_per_100g <= thresholds['energy']:
            score += 0
        elif self.kcal_per_100g <= 335:
            score += 1
        elif self.kcal_per_100g <= 670:
            score += 2
        elif self.kcal_per_100g <= 1005:
            score += 3
        elif self.kcal_per_100g <= 1340:
            score += 4
        elif self.kcal_per_100g <= 1675:
            score += 5
        else:
            score += 10

        
        if self.saturated_fats_per_100g is not None:
            if self.saturated_fats_per_100g <= thresholds['saturated_fats']:
                score += 0
            elif self.saturated_fats_per_100g <= 3:
                score += 1
            elif self.saturated_fats_per_100g <= 4.5:
                score += 2
            elif self.saturated_fats_per_100g <= 6:
                score += 3
            else:
                score += 4

        
        if self.sugars_per_100g is not None:
            if self.sugars_per_100g <= thresholds['sugars']:
                score += 0
            elif self.sugars_per_100g <= 4.5:
                score += 1
            elif self.sugars_per_100g <= 9:
                score += 2
            elif self.sugars_per_100g <= 13.5:
                score += 3
            else:
                score += 4

        
        if self.sodium_per_100g is not None:
            if self.sodium_per_100g <= thresholds['sodium']:
                score += 0
            elif self.sodium_per_100g <= 0.18:
                score += 1
            elif self.sodium_per_100g <= 0.36:
                score += 2
            elif self.sodium_per_100g <= 0.54:
                score += 3
            else:
                score += 4

        
        if score <= 1:
            self.nutriscore = 'A'
        elif score <= 5:
            self.nutriscore = 'B'
        elif score <= 9:
            self.nutriscore = 'C'
        elif score <= 13:
            self.nutriscore = 'D'
        else:
            self.nutriscore = 'E'

    def save(self, *args, **kwargs):
        self.calculate_nutriscore()  
        super().save(*args, **kwargs)

class PendingProduct(models.Model):
    PRODUCT_TYPES = (
        ('None', 'None'),
        ('lactate', 'Lactate'),
        ('carne', 'Carne'),
        ('legume', 'Legume'),
        ('fructe', 'Fructe'),
        
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    product_name = models.CharField(max_length=100)
    brands = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    categories = models.CharField(max_length=200)
    image = models.ImageField(upload_to='pending_product_images/', null=True, blank=True)
    ean_code = models.CharField(max_length=13, unique=True, blank=True, null=True, help_text='European Article Number (EAN) code')
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sugars_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    sodium_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    saturated_fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    allergies = models.TextField(null=True, blank=True)
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    approved = models.BooleanField(default=False)
    nutriscore = models.CharField(max_length=1, null=True, blank=True)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    def __str__(self):
        return self.product_name
    
    def approve(self):
        
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
            sugars_per_100g=self.sugars_per_100g,  
            sodium_per_100g=self.sodium_per_100g,  
            saturated_fats_per_100g=self.saturated_fats_per_100g,  
            approved=True  
        )

        return product
    
    def handle_similar_products(self):
        similar_products = PendingProduct.objects.filter(
            product_name=self.product_name,
            brands=self.brands,
            quantity=self.quantity,
            categories=self.categories,
            protein_per_100g=self.protein_per_100g,
            carbs_per_100g=self.carbs_per_100g,
            fats_per_100g=self.fats_per_100g,
            kcal_per_100g=self.kcal_per_100g,
            price__gte=self.price - 10,
            price__lte=self.price + 10,
            approved=False
        )

        if similar_products.count() >= 4:  
            
            product = Product.objects.create(
                product_name=self.product_name,
                price__gte=self.price - 10,
                price__lte=self.price + 10,
                protein_per_100g__gte=self.protein_per_100g - 10,
                protein_per_100g__lte=self.protein_per_100g + 10,
                carbs_per_100g__gte=self.carbs_per_100g - 10,
                carbs_per_100g__lte=self.carbs_per_100g + 10,
                fats_per_100g__gte=self.fats_per_100g - 10,
                fats_per_100g__lte=self.fats_per_100g + 10,
                kcal_per_100g__gte=self.kcal_per_100g - 10,
                kcal_per_100g__lte=self.kcal_per_100g + 10,
                sugars_per_100g=self.sugars_per_100g,  
                sodium_per_100g=self.sodium_per_100g,  
                saturated_fats_per_100g=self.saturated_fats_per_100g,  
                approved=False
            )

            
            similar_products.delete()

            return product
        else:
            self.save()
            return None



class ApiProduct(models.Model):
    PRODUCT_TYPES = (
        ('None', 'None'),
        ('lactate', 'Lactate'),
        ('carne', 'Carne'),
        ('legume', 'Legume'),
        ('fructe', 'Fructe'),
        
    )
    
    product_name = models.CharField(max_length=255, unique=True)
    brands = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)
    categories = models.CharField(max_length=200)
    image = models.ImageField(upload_to='api_product_images/', null=True, blank=True)  
    ean_code = models.CharField(max_length=13, unique=True, blank=True, null=True, help_text='European Article Number (EAN) code')
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    sugars_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    sodium_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    saturated_fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='None')
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    total_ratings = models.IntegerField(default=0)
    rated_by = models.ManyToManyField(User, through='ApiProductRating')
    allergies = models.TextField(null=True, blank=True)  
    nutriscore = models.CharField(max_length=1, null=True, blank=True)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)

    def __str__(self):
        return self.product_name
    
    def calculate_average_rating(self):
        
        average_rating = self.apiproductrating_set.aggregate(avg_rating=Avg('rating'))['avg_rating']
        if average_rating is not None:
            self.user_rating = average_rating
            self.save()

class Basket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    age_confirmation = models.BooleanField(default=False)

class BasketItem(models.Model):
    BASKET_SOURCES = (
        ('database', 'Database'),
        ('api', 'API'),
    )

    basket = models.ForeignKey(Basket, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    api_product = models.ForeignKey(ApiProduct, null=True, blank=True, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, choices=BASKET_SOURCES)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  

    def save(self, *args, **kwargs):
        if self.product:
            self.price = self.product.price * self.quantity
        elif self.api_product and self.api_product.price is not None:  
            self.price = self.api_product.price * self.quantity
        else:
            self.price = Decimal('0.00')  
        super().save(*args, **kwargs)

    def __str__(self):
        if self.product:
            return f"Product: {self.product.product_name}"
        elif self.api_product:
            return f"API Product: {self.api_product.product_name}"
        else:
            return "Unknown Product"
        
class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    PRODUCT_CHOICES = (
        ('Product', 'Product'),
        ('ApiProduct', 'API Product'),
    )

    product_type = models.CharField(max_length=20, choices=PRODUCT_CHOICES, null=True, blank=True)
    object_id = models.PositiveIntegerField(default=0)  
    product = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=150, null=True, blank=True)
    content = models.TextField()
    product_name = models.CharField(max_length=255, null=True, blank=True)  
    pub_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.product_type} Post"

    def save(self, *args, **kwargs):
        if self.product:
            self.product_name = self.product.product_name  
        super().save(*args, **kwargs)


class Subscriber(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True)
    subscription_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0) 

class ApiProductRating(models.Model):
    product = models.ForeignKey(ApiProduct, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)


class Meal(models.Model):
    MEAL_CHOICES = (
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snacks', 'Snacks'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES)
    products = models.ManyToManyField(Product, through='MealProduct')
    api_products = models.ManyToManyField(ApiProduct, through='MealApiProduct')
    total_calories = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_proteins = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_carbs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_fats = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def update_totals(self):
        
        meal_products = self.mealproduct_set.all()
        total_calories_meal = meal_products.aggregate(
            total_calories=Sum((F('product__kcal_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_calories'] or 0
        total_proteins_meal = meal_products.aggregate(
            total_proteins=Sum((F('product__protein_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_proteins'] or 0
        total_carbs_meal = meal_products.aggregate(
            total_carbs=Sum((F('product__carbs_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_carbs'] or 0
        total_fats_meal = meal_products.aggregate(
            total_fats=Sum((F('product__fats_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_fats'] or 0

        
        meal_api_products = self.mealapiproduct_set.all()
        total_calories_api = meal_api_products.aggregate(
            total_calories=Sum((F('kcal_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_calories'] or 0
        total_proteins_api = meal_api_products.aggregate(
            total_proteins=Sum((F('protein_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_proteins'] or 0
        total_carbs_api = meal_api_products.aggregate(
            total_carbs=Sum((F('carbs_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_carbs'] or 0
        total_fats_api = meal_api_products.aggregate(
            total_fats=Sum((F('fats_per_100g') * F('quantity_grams') / 100), output_field=FloatField())
        )['total_fats'] or 0

        
        self.total_calories = total_calories_meal + total_calories_api
        self.total_proteins = total_proteins_meal + total_proteins_api
        self.total_carbs = total_carbs_meal + total_carbs_api
        self.total_fats = total_fats_meal + total_fats_api
        self.save()

    def add_product(self, product, quantity_grams, user=None):
        if isinstance(product, Product):
            
            kcal_per_100g = product.kcal_per_100g or 0
            protein_per_100g = product.protein_per_100g or 0
            carbs_per_100g = product.carbs_per_100g or 0
            fats_per_100g = product.fats_per_100g or 0

            meal_product = MealProduct.objects.create(
                meal=self,
                product=product,
                quantity_grams=quantity_grams,
                user=user,
                kcal_per_100g=kcal_per_100g,
                protein_per_100g=protein_per_100g,
                carbs_per_100g=carbs_per_100g,
                fats_per_100g=fats_per_100g
            )
            self.update_totals()  
            return meal_product
        elif isinstance(product, ApiProduct):
            
            kcal_per_100g = product.kcal_per_100g or 0
            protein_per_100g = product.protein_per_100g or 0
            carbs_per_100g = product.carbs_per_100g or 0
            fats_per_100g = product.fats_per_100g or 0

            meal_api_product = MealApiProduct.objects.create(
                meal=self,
                api_product=product,
                quantity_grams=quantity_grams,
                user=user,
                kcal_per_100g=kcal_per_100g,
                protein_per_100g=protein_per_100g,
                carbs_per_100g=carbs_per_100g,
                fats_per_100g=fats_per_100g
            )
            self.update_totals()  
            return meal_api_product
        else:
            raise ValueError("Invalid product type")

    def remove_product(self, product):
        
        if isinstance(product, MealProduct):
            product.delete()
            self.update_totals()
        elif isinstance(product, MealApiProduct):
            product.delete()
            self.update_totals()
        else:
            raise ValueError("Invalid product type")

class MealProduct(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_grams = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2)

class MealApiProduct(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    api_product = models.ForeignKey(ApiProduct, on_delete=models.CASCADE)
    quantity_grams = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=2)
    protein_per_100g = models.DecimalField(max_digits=10, decimal_places=2)
    carbs_per_100g = models.DecimalField(max_digits=10, decimal_places=2)
    fats_per_100g = models.DecimalField(max_digits=10, decimal_places=2)


class Discount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    used = models.BooleanField(default=False)

    def __str__(self):
        return self.code


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    pub_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.pub_date}"
    



class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    name = models.CharField(max_length=200, unique=True)
    content = models.TextField()
    description = models.TextField(max_length=500, null=True, blank=True)
    video = models.URLField(null=True, blank=True)


class Ingredient(models.Model):
    RECIPE_SOURCES = (
        ('database', 'Database'),
        ('api', 'API'),
    )

    recipe = models.ForeignKey(Recipe, related_name='ingredients', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE)
    api_product = models.ForeignKey(ApiProduct, null=True, blank=True, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, choices=RECIPE_SOURCES)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        if self.product:
            return f"Product: {self.product.product_name}"
        elif self.api_product:
            return f"API Product: {self.api_product.product_name}"
        else:
            return "Unknown Product"
        

class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}: {self.message}'
    

class Article(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=200, unique=True)
    content = models.TextField()
    description = models.TextField(max_length=500, null=True, blank=True)
    cover = models.ImageField(upload_to='articles/', null=True, blank=True)


class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='articles/', null=True, blank=True)