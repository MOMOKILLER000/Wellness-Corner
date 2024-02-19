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
# views.py
# views.py
def index(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '')
        product_info = search_product(product_name)
        return render(request, 'index.html', {'product_info': product_info, 'searched_product': product_name})
    else:
        # Retrieve products from the database
        database_products = Product.objects.all()

        # Retrieve user allergies if authenticated
        common_allergies = []
        if request.user.is_authenticated:
            user_allergies = request.user.allergies.all()

            # Find common allergies with database products
            for product in database_products:
                allergies_list = product.allergies.split(',') if product.allergies else []  # Parse allergies string into a list
                if allergies_list and set(allergies_list) & set(allergy.name for allergy in user_allergies):
                    common_allergies.extend(allergies_list)  # Extend the list of common allergies

        # Pass the combined product information and common allergies to the template
        return render(request, 'index.html', {'product_info': database_products, 'common_allergies': set(common_allergies)})


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

def search_product(product_name, exclude_allergy=None):
    # Search for products in both local database and external API
    database_products = Product.objects.filter(product_name__icontains=product_name)
    
    api_url = f'https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1'
    response = requests.get(api_url)
    if response.status_code == 200:
        product_data = response.json()
        if 'products' in product_data:
            api_products = []
            for product in product_data['products']:
                # Extracting data
                name = product.get('product_name', '')
                brands = product.get('brands', '')
                quantity = product.get('quantity', '')
                categories = product.get('categories', '')
                nutriments = product.get('nutriments', {})
                protein_per_100g = nutriments.get('proteins_100g', '')
                carbs_per_100g = nutriments.get('carbohydrates_100g', '')
                fats_per_100g = nutriments.get('fat_100g', '')
                kcal_per_100g = nutriments.get('energy-kcal_100g', '')
                allergies = product.get('allergens_tags', [])  # Fetching allergies

                # Handle empty string values
                protein_per_100g = Decimal(protein_per_100g) if protein_per_100g else None
                carbs_per_100g = Decimal(carbs_per_100g) if carbs_per_100g else None
                fats_per_100g = Decimal(fats_per_100g) if fats_per_100g else None
                kcal_per_100g = Decimal(kcal_per_100g) if kcal_per_100g else None
                
                # Remove prefix and only keep the allergy name
                cleaned_allergies = [allergy.split(":")[1] if ":" in allergy else allergy for allergy in allergies]

                # Check if the product has the specified allergy
                if exclude_allergy and any(exclude_allergy.lower() in allergy.lower() for allergy in cleaned_allergies):
                    continue  # Skip this product

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
                        'allergies': json.dumps(cleaned_allergies)   # Save allergies as JSON string
                    }
                )
                api_product.allergies = cleaned_allergies
                api_product.save()

                api_products.append(api_product)

            if api_products:
                return list(database_products) + api_products  # Combine both database and API products
    return list(database_products)



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
