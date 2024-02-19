# views.py
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from .models import Product, ApiProduct
import requests
from decimal import Decimal
from django.core.exceptions import ValidationError


def index(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '')
        product_info = search_product(product_name)
        return render(request, 'index.html', {'product_info': product_info, 'searched_product': product_name})
    else:
        # Retrieve products from the database
        database_products = Product.objects.all()
        
        # Retrieve products from the API
        api_products = search_product("")  # Fetch all API products
        
        product_info = list(database_products) + api_products
        return render(request, 'index.html', {'product_info': product_info})

def search_product(product_name):
    # Search in the API for exact match
    api_url = f'https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1'
    response = requests.get(api_url)
    if response.status_code == 200:
        product_data = response.json()
        if 'products' in product_data:
            api_products = []
            for product in product_data['products']:
                name = product.get('product_name', '')
                brands = product.get('brands', '')
                quantity = product.get('quantity', '')
                categories = product.get('categories', '')
                nutriments = product.get('nutriments', {})
                protein_per_100g = nutriments.get('proteins_100g', '')
                carbs_per_100g = nutriments.get('carbohydrates_100g', '')
                fats_per_100g = nutriments.get('fat_100g', '')
                kcal_per_100g = nutriments.get('energy-kcal_100g', '')
                
                # Handle empty string values
                protein_per_100g = Decimal(protein_per_100g) if protein_per_100g else None
                carbs_per_100g = Decimal(carbs_per_100g) if carbs_per_100g else None
                fats_per_100g = Decimal(fats_per_100g) if fats_per_100g else None
                kcal_per_100g = Decimal(kcal_per_100g) if kcal_per_100g else None
                
                # Create or update API product
                api_product, created = ApiProduct.objects.get_or_create(
                    product_name=name,
                    defaults={
                        'brands': brands,
                        'quantity': quantity,
                        'categories': categories,
                        'protein_per_100g': protein_per_100g,
                        'carbs_per_100g': carbs_per_100g,
                        'fats_per_100g': fats_per_100g,
                        'kcal_per_100g': kcal_per_100g,
                    }
                )
                api_products.append(api_product)
                
            if api_products:
                return api_products
    return []

def rate_product(request, product_id, source):
    if request.method == 'POST':
        try:
            rating = Decimal(request.POST.get('rating'))  # Convert rating to Decimal
        except ValueError:
            return HttpResponseBadRequest("Invalid rating")

        try:
            if source == 'database':
                product = Product.objects.get(pk=product_id)
            elif source == 'api':
                product = ApiProduct.objects.get(pk=product_id)
            else:
                return HttpResponseBadRequest("Invalid source")

            if product.user_rating is None:
                product.user_rating = rating
            else:
                # Update the rating by averaging with previous ratings
                product.user_rating = (product.user_rating + rating) / Decimal(2)
            product.save()
        except (Product.DoesNotExist, ApiProduct.DoesNotExist):
            return HttpResponseBadRequest("Product not found")
        except ValidationError:
            return HttpResponseBadRequest("Invalid rating")

    return redirect('index')
