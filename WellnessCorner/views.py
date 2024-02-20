from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest
from django.contrib.auth import authenticate, login
from .models import Product, ApiProduct, Allergy
from .forms import RegistrationForm, AllergyForm
import requests
from decimal import Decimal
import json
from django.contrib import messages 
from django.core.exceptions import ValidationError

def index(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '')
        product_info = search_product(product_name, user=request.user)
        # Set the source attribute for each product based on its type
        for product in product_info:
            if isinstance(product, Product):
                product.source = 'database'
            elif isinstance(product, ApiProduct):
                product.source = 'api'
            else:
                # Handle other cases if needed
                pass
        return render(request, 'index.html', {'product_info': product_info, 'searched_product': product_name})
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
            return redirect('index')  # Redirect to the index page upon successful login
        else:
            messages.error(request, 'Invalid login credentials. Please try again.')

    return render(request, 'login.html')

def search_product(product_name, user=None):
    database_products = Product.objects.filter(product_name__icontains=product_name)
    api_products = []

    # Fetch data from API if applicable
    if user and user.is_authenticated:
        user_allergies = user.allergies.all()

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

                allergies = [allergy.split(':')[1] for allergy in allergies]

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
                        'allergies': json.dumps(allergies) if allergies else None
                    }
                )
                api_products.append(api_product)

    # Combine database products and API products, and remove duplicates based on product name
    all_products = list(database_products) + api_products
    unique_products = {product.product_name: product for product in all_products}.values()

    return unique_products

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
                product.user_rating = (product.user_rating + rating) / Decimal(2)
            product.save()
        except (Product.DoesNotExist, ApiProduct.DoesNotExist):
            return HttpResponseBadRequest("Product not found")
        except ValidationError:
            return HttpResponseBadRequest("Invalid rating")

    return redirect('index')

def product_detail(request, product_id, source):
    try:
        if source == 'database':
            product_model = Product
        elif source == 'api':
            product_model = ApiProduct
        else:
            return HttpResponseBadRequest("Invalid source")

        product = get_object_or_404(product_model, pk=product_id)

        # Parse product's allergies based on the source
        if source == 'database':
            product_allergies = []
            if product.allergies:
                product_allergies = product.allergies.split(',')  # Split by comma to get a list of allergies
        elif source == 'api':
            product_allergies = []
            if product.allergies:
                product_allergies = json.loads(product.allergies)

        # Get the current user's allergies if logged in
        user_allergies = []
        if request.user.is_authenticated:
            user_allergies = request.user.allergies.all()

        # Find common allergies between the product and the user
        common_allergies = set(product_allergies) & set(allergy.name for allergy in user_allergies)

        # Get product rating
        product_rating = getattr(product, 'user_rating', None)

        return render(request, 'product_detail.html', {'product': product, 'common_allergies': common_allergies, 'product_rating': product_rating, 'source': source})
    except product_model.DoesNotExist:
        return HttpResponseBadRequest("Product not found")

def add_to_basket(request, product_id, source):
    if request.method == 'POST':
        # Check if source is either 'database' or 'api'
        if source not in ['database', 'api']:
            return HttpResponseBadRequest("Invalid source")

        # Determine the model based on the source
        if source == 'database':
            product_model = Product
        elif source == 'api':
            product_model = ApiProduct

        # Get the product based on the model and product_id
        product = get_object_or_404(product_model, pk=product_id)

        # Assuming you have a simple solution to store basket items in session
        basket = request.session.get('basket', [])
        basket.append({'product_id': product_id, 'source': source})
        request.session['basket'] = basket

        return redirect('basket_page')  # Redirect to the basket page

    # Handle other request methods if needed
    return HttpResponseBadRequest("Invalid request method")

def basket_page(request):
    basket = request.session.get('basket', [])
    products_in_basket = []

    total_price = Decimal('0.00')  # Initialize total_price as a Decimal

    for item in basket:
        product_id = item['product_id']
        source = item['source']

        product_model = None
        if source == 'database':
            product_model = Product
        elif source == 'api':
            product_model = ApiProduct

        product = get_object_or_404(product_model, pk=product_id)

        # Check if product has a valid price before adding it to total_price
        if product.price is not None:
            total_price += product.price

        products_in_basket.append(product)

    return render(request, 'basket.html', {'products_in_basket': products_in_basket, 'total_price': total_price})
