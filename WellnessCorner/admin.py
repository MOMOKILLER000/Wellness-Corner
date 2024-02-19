from django.contrib import admin
from .models import Product, ApiProduct

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
