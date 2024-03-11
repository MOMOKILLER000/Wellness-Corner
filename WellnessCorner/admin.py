from django.contrib import admin
from .models import Product, ApiProduct, Allergy, Basket, BasketItem, PendingProduct, Post, Subscriber, ApiProductRating, ProductRating
from .models import Meal, MealApiProduct, MealProduct, UserProfile, Discount, Comment, Banned
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'brands', 'quantity', 'categories', 'product_type']
    list_filter = ['product_name', 'brands', 'categories', 'product_type']
    search_fields = ['product_name']

class ApiProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'brands', 'quantity', 'categories', 'product_type']
    list_filter = ['product_name', 'brands', 'categories', 'product_type']
    search_fields = ['product_name']

admin.site.register(Product, ProductAdmin)
admin.site.register(ApiProduct, ApiProductAdmin)
admin.site.register(User)
admin.site.register(Allergy)
admin.site.register(Basket)
admin.site.register(BasketItem)
admin.site.register(PendingProduct)
admin.site.register(Post)
admin.site.register(Subscriber)
admin.site.register(ApiProductRating)
admin.site.register(ProductRating)
admin.site.register(MealProduct)
admin.site.register(Meal)
admin.site.register(MealApiProduct)
admin.site.register(UserProfile)
admin.site.register(Discount)
admin.site.register(Comment)
admin.site.register(Banned)