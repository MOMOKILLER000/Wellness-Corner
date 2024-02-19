# views.py
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.contrib.auth import authenticate, login
from .models import Product, ApiProduct
from .forms import RegistrationForm
import requests
from decimal import Decimal
import json
from django.contrib import messages 
from .forms import AllergyForm # Import the form for adding allergies
from .models import User
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
# views.py
# views.py
def index(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '')
        product_info, common_allergies = search_product(product_name, user=request.user)
        return render(request, 'index.html', {'product_info': product_info, 'common_allergies': common_allergies, 'searched_product': product_name})
    else:
        return render(request, 'index.html')


def registration_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            form.save_m2m()  # Save many-to-many relationships (allergies)
            return redirect('index')
    else:
        form = RegistrationForm()
    
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            # Redirect to the exploresphere page upon successful login
            return redirect('index')
        else:
            messages.error(request, 'Invalid login credentials. Please try again.')

    return render(request, 'login.html')

def add_allergy(request):
    if request.method == 'POST':
        form = AllergyForm(request.POST)
        if form.is_valid():
            allergy = form.save()  # Save allergy instance
            # You may want to associate this allergy with the current user
            # For example:
            # request.user.allergies.add(allergy)
            return redirect('register')  # Redirect to registration page after adding allergy
    else:
        form = AllergyForm()

    # If form is invalid, or it's a GET request, render the registration page again with the form
    return render(request, 'register.html', {'allergy_form': form})

def search_product(product_name, exclude_allergy=None, user=None):
    # Search for products in both local database and external API
    database_products = Product.objects.filter(product_name__icontains=product_name)
    api_products = []

    # Retrieve user allergies if authenticated
    common_allergies = set()
    if user and user.is_authenticated:
        user_allergies = user.allergies.all()

        # Calculate common allergies for database products
        for product in database_products:
            if product.allergies:
                allergies_list = json.loads(product.allergies)  # Parse allergies JSON string
                common_allergies.update(set(allergies_list) & set(allergy.name for allergy in user_allergies))

    # Fetch products from the external API
    api_url = f'https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1'
    response = requests.get(api_url)
    if response.status_code == 200:
        product_data = response.json()
        if 'products' in product_data:
            for product in product_data['products']:
                name = product.get('product_name', '')
                brands = product.get('brands', '')
                quantity = product.get('quantity', '')
                categories = product.get('categories', '')
                nutriments = product.get('nutriments', {})
                protein_per_100g = Decimal(nutriments.get('proteins_100g', '')) if nutriments.get(
                    'proteins_100g', '') else None
                carbs_per_100g = Decimal(nutriments.get('carbohydrates_100g', '')) if nutriments.get(
                    'carbohydrates_100g', '') else None
                fats_per_100g = Decimal(nutriments.get('fat_100g', '')) if nutriments.get('fat_100g', '') else None
                kcal_per_100g = Decimal(nutriments.get('energy-kcal_100g', '')) if nutriments.get(
                    'energy-kcal_100g', '') else None
                allergies = product.get('allergens_tags', [])

                # Extract actual allergy names from the list
                allergies = [allergy.split(':')[1] for allergy in allergies]

                # Create or update API product
                api_product, created = ApiProduct.objects.update_or_create(
                    product_name=name,
                    defaults={
                        'brands': brands,
                        'quantity': quantity,
                        'categories': categories,
                        'protein_per_100g': protein_per_100g,
                        'carbs_per_100g': carbs_per_100g,
                        'fats_per_100g': fats_per_100g,
                        'kcal_per_100g': kcal_per_100g,
                        'allergies': json.dumps(allergies)  # Save allergies as JSON string
                    }
                )
                api_products.append(api_product)

                # Calculate common allergies for API products
                if user and user.is_authenticated:
                    common_allergies.update(set(allergies) & set(allergy.name for allergy in user_allergies))

    # Combine database and API products
    all_products = list(database_products) + api_products

    return all_products, common_allergies




def rate_product(request, product_id, source):
    if request.method == 'POST':
        try:
            rating = Decimal(request.POST.get('rating'))  # Convert rating to Decimal
        except ValueError:
            return HttpResponseBadRequest("Invalid rating")

        try:
            if source == 'database':
                product_model = Product
            elif source == 'api':
                product_model = ApiProduct
            else:
                return HttpResponseBadRequest("Invalid source")

            product = product_model.objects.get(pk=product_id)

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
