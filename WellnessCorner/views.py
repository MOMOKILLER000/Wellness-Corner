from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth import authenticate, login
from .models import Product, ApiProduct, Allergy, Basket, BasketItem
from .forms import RegistrationForm
import requests
from decimal import Decimal
import json
from django.contrib import messages 
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ProductForm
from .models import PendingProduct

@login_required
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
def logout_view(request):
    logout(request)
    return redirect('login')
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

                # Fetch product rating from the database for API product
                try:
                    api_product = ApiProduct.objects.get(product_name=name)
                    rating = api_product.user_rating
                except ApiProduct.DoesNotExist:
                    rating = None

                api_product.user_rating = rating  # Set the rating for the API product
                api_products.append(api_product)

    # Combine database products and API products
    all_products = list(database_products) + api_products

    # Create a dictionary of unique products based on product name
    unique_products = {product.product_name: product for product in all_products}

    return unique_products.values()



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

            # Get the common allergies for rendering in the template
            common_allergies = None

            if source == 'database':
                product_allergies = product.allergies.split(',') if product.allergies else []
            elif source == 'api':
                product_allergies = json.loads(product.allergies) if product.allergies else []

            user_allergies = request.user.allergies.all()
            common_allergies = set(product_allergies) & set(allergy.name for allergy in user_allergies)

            # Render the same product detail template with the updated rating
            return render(request, 'product_detail.html', {'product': product, 'common_allergies': common_allergies, 'product_rating': product.user_rating, 'source': source})

        except (Product.DoesNotExist, ApiProduct.DoesNotExist):
            return HttpResponseBadRequest("Product not found")
        except ValidationError:
            return HttpResponseBadRequest("Invalid rating")

    return HttpResponseBadRequest("Invalid request method")


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

        # Get or create the basket for the current user
        basket, created = Basket.objects.get_or_create(user=request.user)

        # Add the product to the basket
        if source == 'database':
            BasketItem.objects.create(basket=basket, product=product, source=source)
        elif source == 'api':
            BasketItem.objects.create(basket=basket, api_product=product, source=source)

        return redirect('basket_page')  # Redirect to the basket page

    # Handle other request methods if needed
    return HttpResponseBadRequest("Invalid request method")
@login_required
def basket_page(request):
    # Get the basket for the current user
    basket, created = Basket.objects.get_or_create(user=request.user)

    # Fetch items from the database
    items = basket.items.select_related('product', 'api_product')

    total_price = Decimal('0.00')  # Initialize total_price as a Decimal

    products_in_basket = []
    for item in items:
        if item.product:
            product = item.product
            source = 'database'
        elif item.api_product:
            product = item.api_product
            source = 'api'
        else:
            continue

        # Check if product has a valid price before adding it to total_price
        if product.price is not None:
            total_price += product.price

        products_in_basket.append({'product': product, 'source': source})

    return render(request, 'basket.html', {'products_in_basket': products_in_basket, 'total_price': total_price})

def delete_from_basket(request, product_id, source):
    if request.method == 'POST':
        # Check if source is either 'database' or 'api'
        if source not in ['database', 'api']:
            return JsonResponse({'error': 'Invalid source'}, status=400)

        # Find the basket item to delete based on product_id, source, and user
        basket_item = BasketItem.objects.filter(
            basket__user=request.user,
            source=source,
            product_id=product_id if source == 'database' else None,
            api_product_id=product_id if source == 'api' else None
        ).first()

        if basket_item:
            basket_item.delete()
            return redirect('basket_page')  # Redirect to the basket page after successful deletion
        else:
            return JsonResponse({'error': 'Item not found'}, status=404)

    # Return error for invalid request method
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            existing_pending_products = PendingProduct.objects.filter(
                product_name=product.product_name,
                brands=product.brands,
                quantity=product.quantity,
                categories=product.categories,
                protein_per_100g=product.protein_per_100g,
                carbs_per_100g=product.carbs_per_100g,
                fats_per_100g=product.fats_per_100g,
                kcal_per_100g=product.kcal_per_100g,
                price=product.price,
                product_type=product.product_type,
                user_rating=product.user_rating,
                allergies=product.allergies,
                approved=False
            )

            if existing_pending_products.count() >= 4:
                approved_product = existing_pending_products.first().handle_similar_products()
                if approved_product:
                    messages.success(request, f'Product "{approved_product.product_name}" approved and moved to Products.')
                else:
                    messages.success(request, 'Product creation pending approval.')
            else:
                # Save the new PendingProduct
                pending_product = form.save(commit=False)
                pending_product.superuser = request.user  # Assign the current user as the superuser
                pending_product.save()
                messages.success(request, 'Product creation pending approval.')
            return redirect('index')  # Redirect to the index page
    else:
        form = ProductForm()

    return render(request, 'create.html', {'form': form})

@login_required
def approve_products(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to access this page.")

    pending_products = PendingProduct.objects.filter(approved=False)
    if request.method == 'POST':
        approved_products = request.POST.getlist('approved_products')
        for product_id in approved_products:
            pending_approval = PendingProduct.objects.get(id=product_id)
            # Create a new Product instance based on the pending_approval
            product = pending_approval.approve_and_move_to_product()
            messages.success(request, f'Product "{product.product_name}" approved and moved to Products.')
        
        # Delete all approved pending products
        pending_products.filter(id__in=approved_products).delete()

        return redirect('pending_products_list')  # Redirect to the list of pending products after approval

    return render(request, 'pending_products.html', {'pending_products': pending_products})


def pending_products(request):
    pending_products = PendingProduct.objects.all()  # Query all pending products
    return render(request, 'pending_products.html', {'pending_products': pending_products})