from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth import authenticate, login, logout
from .models import Product, ApiProduct, Allergy, Basket, BasketItem, ProductRating, ApiProductRating, UserProfile, Discount
from .forms import RegistrationForm, LoginForm, UserProfileForm
import requests
from decimal import Decimal
import json
from django.contrib import messages 
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ProductForm
from .models import PendingProduct, Subscriber
from django.core.files.base import ContentFile
from django.http import HttpResponseForbidden
from django.conf import settings
from .forms import PostForm, EmailSubscriberForm, ContactForm, NewsletterSubscriptionForm, CustomPasswordChangeForm, CommentForm
from .models import Post, Comment, User
from itertools import chain
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Meal, MealProduct, MealApiProduct, Banned
from .forms import MealProductForm, MealApiProductForm, UserAccountForm
from django.http import HttpResponse
from django.db.models import FloatField
from django.db.models import Sum, F, FloatField
from django.http import Http404
from django.contrib.auth.views import PasswordChangeView
import uuid
import string
import random
from datetime import timedelta
from django.utils import timezone

@login_required
def index(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '')
        if product_name.strip():  # Check if the search query is not empty
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
            return render(request, 'index.html', {'search_query': product_name, 'search_results': product_info})
        else:  # If the search query is empty, display the default products
            best_rated_products = Product.objects.filter(user_rating__isnull=False).order_by('-user_rating')[:4]
            cheapest_products = Product.objects.filter(price__gt=0).order_by('price')[:4]
            return render(request, 'index.html', {'best_rated_products': best_rated_products, 'cheapest_products': cheapest_products})
    else:
        # Get the top 4 best-rated products from both models
        best_rated_products = sorted(
            chain(Product.objects.filter(user_rating__isnull=False), ApiProduct.objects.filter(user_rating__isnull=False)),
            key=lambda x: x.user_rating if x.user_rating else float('-inf'),
            reverse=True
        )[:4]
        
        # Get the top 4 cheapest products from both models
        cheapest_products = sorted(
            chain(Product.objects.filter(price__gt=0), ApiProduct.objects.filter(price__gt=0)),
            key=lambda x: x.price
        )[:4]
        
        # Set the source attribute for each product based on its type
        for product in chain(best_rated_products, cheapest_products):
            if isinstance(product, Product):
                product.source = 'database'
            elif isinstance(product, ApiProduct):
                product.source = 'api'
            else:
                # Handle other cases if needed
                pass
        
        return render(request, 'index.html', {'best_rated_products': best_rated_products, 'cheapest_products': cheapest_products})
    

def registration_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Add reCAPTCHA verification here
            response_token = request.POST.get('g-recaptcha-response', '')
            if verify_recaptcha(response_token):
                user = form.save(commit=False)
                user.save()
                form.save_m2m()  # Save many-to-many relationships (allergies)
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, 'reCAPTCHA verification failed. Please try again.')
        else:
            messages.error(request, 'Invalid form submission. Please correct the errors.')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Add reCAPTCHA verification here
            response_token = request.POST.get('g-recaptcha-response', '')
            if verify_recaptcha(response_token):
                email = form.cleaned_data.get('email')
                password = form.cleaned_data.get('password')
                user = authenticate(request, email=email, password=password)

                if user is not None:
                    login(request, user)
                    return redirect('index')
                else:
                    messages.error(request, 'Invalid login credentials. Please try again.')
            else:
                messages.error(request, 'reCAPTCHA verification failed. Please try again.')
        else:
            messages.error(request, 'Invalid form submission. Please correct the errors.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def verify_recaptcha(response_token):
    secret_key = '6Le2Qn4pAAAAAPMo61FnEEKdFKApauuRG9dh0Hrt'  # Replace 'YOUR_SECRET_KEY' with your actual secret key obtained from the reCAPTCHA admin console
    payload = {
        'secret': secret_key,
        'response': response_token
    }
    response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = response.json()
    return result['success']


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def myaccount(request):
    user = request.user

    if request.method == 'POST':
        form = UserAccountForm(request.POST, instance=user)
        password_change_form = CustomPasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')

            # Check if the password change form is valid before saving
            if password_change_form.is_valid():
                password_change_form.save()
                messages.success(request, 'Password updated successfully.')

            return redirect('myaccount')  # Redirect to the profile page after successful update

    else:
        form = UserAccountForm(instance=user)
        password_change_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'myaccount.html', {'form': form, 'password_change_form': password_change_form})

class CustomPasswordChangeView(PasswordChangeView):
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Password changed successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid credentials')
        return redirect('myaccount')

def search_product(product_name, user=None):
    # Fetch database products matching the search term
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
                sugars_per_100g = Decimal(nutriments.get('sugars_100g', '')) if nutriments.get(
                    'sugars_100g', '') else None
                sodium_per_100g = Decimal(nutriments.get('sodium_100g', '')) if nutriments.get(
                    'sodium_100g', '') else None
                saturated_fats_per_100g = Decimal(nutriments.get('saturated-fat_100g', '')) if nutriments.get(
                    'saturated-fat_100g', '') else None
                kcal_per_100g = Decimal(nutriments.get('energy-kcal_100g', '')) if nutriments.get(
                    'energy-kcal_100g', '') else None
                nutriscore_grade = product.get('nutriscore_grade', None)
                allergies = product.get('allergens_tags', [])
                allergies = [allergy.split(':')[1] for allergy in allergies]
                if nutriscore_grade is not None:
                    nutriscore_grade = nutriscore_grade.upper()
                api_product, created = ApiProduct.objects.get_or_create(
                    product_name=name,
                    defaults={
                        'brands': brands,
                        'quantity': quantity,
                        'categories': categories,
                        'protein_per_100g': protein_per_100g,
                        'carbs_per_100g': carbs_per_100g,
                        'fats_per_100g': fats_per_100g,
                        'sugars_per_100g': sugars_per_100g,
                        'sodium_per_100g': sodium_per_100g,
                        'saturated_fats_per_100g': saturated_fats_per_100g,
                        'kcal_per_100g': kcal_per_100g,
                        'nutriscore': nutriscore_grade,
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

                # Fetch and save image for each API product if it's not already saved
                if product.get('image_url') and not api_product.image:
                    image_url = product.get('image_url')
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        # Save the image to the product
                        api_product.image.save(f'{name}_image.jpg', ContentFile(response.content), save=True)

    # Combine database products and API products
    all_products = list(database_products) + api_products

    # Create a dictionary of unique products based on product name
    unique_products = {product.product_name: product for product in all_products}

    return unique_products.values()

def rate_product(request, product_id, source):
    if request.method == 'POST':
        try:
            rating_value = Decimal(request.POST.get('rating'))  # Convert rating to Decimal
        except ValueError:
            return HttpResponseBadRequest("Invalid rating")

        if rating_value < 0 or rating_value > 10:  # Ensure rating value is within valid range
            return HttpResponseBadRequest("Rating value must be between 0 and 10")

        try:
            if source == 'database':
                product_model = Product
                rating_model = ProductRating
            elif source == 'api':
                product_model = ApiProduct
                rating_model = ApiProductRating
            else:
                return HttpResponseBadRequest("Invalid source")

            product = get_object_or_404(product_model, pk=product_id)

            # Check if the user has already rated the product
            rating, created = rating_model.objects.get_or_create(user=request.user, product=product)

            # Set the rating value
            rating.rating = rating_value
            rating.save()

            # Recalculate the average rating for the product
            product.calculate_average_rating()

            # Get common allergies
            product_allergies = json.loads(product.allergies) if product.allergies else []
            user_allergies = request.user.allergies.all() if request.user.is_authenticated else []
            common_allergies = set(product_allergies) & set(allergy.name for allergy in user_allergies)

            # Render the product detail template with the updated rating and common allergies
            return render(request, 'product_detail.html', {'product': product, 'common_allergies': common_allergies, 'product_rating': product.user_rating, 'source': source})

        except (Product.DoesNotExist, ApiProduct.DoesNotExist):
            return HttpResponseBadRequest("Product not found")

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

@login_required
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

        # Get the basket for the current user
        basket, created = Basket.objects.get_or_create(user=request.user)

        # Check if the product is already in the basket
        if source == 'database':
            existing_item = basket.items.filter(product=product, api_product=None)
        elif source == 'api':
            existing_item = basket.items.filter(api_product=product, product=None)

        if existing_item.exists():
            # Update the quantity of the existing basket item
            existing_item.update(quantity=F('quantity') + 1)
        else:
            # Add the product to the basket with quantity=1
            if source == 'database':
                BasketItem.objects.create(basket=basket, product=product, source=source)
            elif source == 'api':
                BasketItem.objects.create(basket=basket, api_product=product, source=source, quantity=1)

        return redirect('basket_page')  # Redirect to the basket page

    # Handle other request methods if needed
    return HttpResponseBadRequest("Invalid request method")

@login_required
def increment_quantity(request, product_id, source):
    try:
        # Get the basket item for the given product_id and source
        if source == 'database':
            basket_item = BasketItem.objects.get(product_id=product_id, source=source, basket__user=request.user)
        elif source == 'api':
            basket_item = BasketItem.objects.get(api_product_id=product_id, source=source, basket__user=request.user)

        if basket_item.quantity < 20:  # Check if quantity is less than 20
            basket_item.quantity += 1
            basket_item.save()
        else:
            messages.warning(request, "Maximum quantity reached (20).")
    except BasketItem.DoesNotExist:
        messages.error(request, "Basket item not found.")
    return redirect('basket_page')

@login_required
def decrement_quantity(request, product_id, source):
    try:
        # Get the basket item for the given product_id and source
        if source == 'database':
            basket_item = BasketItem.objects.get(product_id=product_id, source=source, basket__user=request.user)
        elif source == 'api':
            basket_item = BasketItem.objects.get(api_product_id=product_id, source=source, basket__user=request.user)

        if basket_item.quantity > 1:
            basket_item.quantity -= 1
            basket_item.save()
        else:
            messages.warning(request, "Quantity cannot be less than 1.")
    except BasketItem.DoesNotExist:
        messages.error(request, "Basket item not found.")
    return redirect('basket_page')

def basket_page(request):
    # Get the basket for the current user
    basket, created = Basket.objects.get_or_create(user=request.user)

    # Fetch items from the database
    items = basket.items.select_related('product', 'api_product')

    total_price = Decimal('0.00')  # Initialize total_price as a Decimal

    products_in_basket = []
    total_health_rating = Decimal('0.00')
    total_quantity = 0

    for item in items:
        if item.product or item.api_product:
            if item.product:
                product = item.product
                source = 'database'
            else:
                product = item.api_product
                source = 'api'

            quantity = item.quantity
            total_quantity += quantity

            # Check if the product has a valid price before adding it to total_price
            if product.price is not None:
                total_price += Decimal(product.price) * quantity

            if product.nutriscore:
                # Calculate the contribution of this product to the basket health rating
                health_rating_contribution = calculate_health_rating(product.nutriscore) * quantity
                total_health_rating += health_rating_contribution
                products_in_basket.append({'product': product, 'source': source, 'quantity': quantity})

    # Fetch used discounts for the user
    used_discounts = Discount.objects.filter(user=request.user, used=True)

    # Calculate the total discount amount
    total_discount_amount = Decimal('0.00')
    for discount in used_discounts:
        total_discount_amount += total_price * (discount.amount / Decimal(100))

    total_price_after_discount = total_price - total_discount_amount
    savings = total_price - total_price_after_discount

    if not products_in_basket:  # If the basket is empty, redirect to the empty basket page
        return render(request, 'basket_empty.html')

    # Calculate the average health rating per item in the basket
    if total_quantity > 0:
        average_health_rating = total_health_rating / total_quantity
    else:
        average_health_rating = Decimal('0.00')

    # Map average_health_rating from 0.0 to 1.0 to A to E
    average_health_rating_mapped = map_health_rating(average_health_rating)

    # Pass the total_price, total_price_after_discount, and used discounts to the template
    return render(request, 'basket.html', {'products_in_basket': products_in_basket, 'total_price': total_price,
                                            'total_price_after_discount': total_price_after_discount, 'savings': savings,
                                            'used_discounts': used_discounts, 'average_health_rating': average_health_rating_mapped})

def calculate_health_rating(nutriscore):
    # Define the mapping from nutriscore to health rating
    health_rating_map = {
        'A': Decimal('0.9'),
        'B': Decimal('0.7'),
        'C': Decimal('0.5'),
        'D': Decimal('0.3'),
        'E': Decimal('0.1'),
    }

    return health_rating_map.get(nutriscore, Decimal('0.1'))  # Default to 'E' rating if nutriscore is unknown

def map_health_rating(health_rating):
    # Map health rating from 0.0 to 1.0 to A to E
    if health_rating >= Decimal('0.8'):
        return 'A'
    elif health_rating >= Decimal('0.6'):
        return 'B'
    elif health_rating >= Decimal('0.4'):
        return 'C'
    elif health_rating >= Decimal('0.2'):
        return 'D'
    else:
        return 'E'

@login_required
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
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user  # Get the current user
            
            # Check if a pending product with the same name exists for the current user
            existing_pending_product = PendingProduct.objects.filter(
                product_name=form.cleaned_data['product_name'],
                user=user
            ).exists()
            
            if existing_pending_product:
                messages.error(request, f'A pending product with the name "{form.cleaned_data["product_name"]}" already exists.')
                return render(request, 'create.html', {'form': form})  # Render the page with the form and error message
            
            product = form.save(commit=False)
            product.user = user
            product.save()  # Save the product first
            
            # Define the margin for price and nutritional data
            price_margin = 10
            nutritional_margin = 10
            
            existing_pending_products = PendingProduct.objects.filter(
                product_name=product.product_name,
                approved=False,
                price__gte=product.price - price_margin,
                price__lte=product.price + price_margin,
                protein_per_100g__gte=product.protein_per_100g - nutritional_margin,
                protein_per_100g__lte=product.protein_per_100g + nutritional_margin,
                carbs_per_100g__gte=product.carbs_per_100g - nutritional_margin,
                carbs_per_100g__lte=product.carbs_per_100g + nutritional_margin,
                fats_per_100g__gte=product.fats_per_100g - nutritional_margin,
                fats_per_100g__lte=product.fats_per_100g + nutritional_margin,
                kcal_per_100g__gte=product.kcal_per_100g - nutritional_margin,
                kcal_per_100g__lte=product.kcal_per_100g + nutritional_margin,
            )

            if existing_pending_products.count() >= 5:
                # Extract the last appended product
                last_appended_product = existing_pending_products.last()
                # Approve one of the pending products and delete the others
                approved_product = last_appended_product.handle_similar_products()
                if approved_product:
                    approved_product.approved = True  # Mark as approved
                    approved_product.save()
                    messages.success(request, f'Product "{approved_product.product_name}" approved and moved to Products.')
                    # Delete the last appended product
                    last_appended_product.delete()
                else:
                    messages.success(request, 'Product creation pending approval.')
            elif existing_pending_products.count() >= 4:
                # Delete excess similar pending products
                last_appended_product = existing_pending_products.last()
                existing_pending_products.exclude(id=last_appended_product.id).delete()
                # Create a new product using the data from the last pending product
                pending_product = last_appended_product
                product = Product.objects.create(
                    product_name=pending_product.product_name,
                    brands=pending_product.brands,
                    quantity=pending_product.quantity,
                    categories=pending_product.categories,
                    protein_per_100g=pending_product.protein_per_100g,
                    carbs_per_100g=pending_product.carbs_per_100g,
                    fats_per_100g=pending_product.fats_per_100g,
                    sugars_per_100g=pending_product.sugars_per_100g,  # Added
                    sodium_per_100g=pending_product.sodium_per_100g,  # Added
                    saturated_fats_per_100g=pending_product.saturated_fats_per_100g,  # Added
                    kcal_per_100g=pending_product.kcal_per_100g,
                    price=pending_product.price,
                    product_type=pending_product.product_type,
                    user_rating=pending_product.user_rating,
                    allergies=pending_product.allergies,
                    approved=True, 
                    image=pending_product.image
                )
                messages.success(request, 'New product created.')
                # Delete the last appended product
                last_appended_product.delete()
            else:
                # Save the pending product
                product.save()
                
            return redirect('product_created') # Redirect to the success page
    else:
        form = ProductForm()

    return render(request, 'create.html', {'form': form})

@login_required
def product_created(request):
    # Render a page confirming that the product was successfully created
    return render(request, 'product_created.html')

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
            product = pending_approval.approve()
            # Copy image from pending product to approved product
            product.image = pending_approval.image
            product.save()
            messages.success(request, f'Product "{product.product_name}" approved and moved to Products.')
        
        # Delete all approved pending products
        pending_products.filter(id__in=approved_products).delete()

        return redirect('pending_products') # Redirect to the list of pending products after approval

    return render(request, 'pending_products.html', {'pending_products': pending_products})

def pending_products(request):
    pending_products = PendingProduct.objects.all()  # Query all pending products
    return render(request, 'pending_products.html', {'pending_products': pending_products})

@login_required
def my_products(request):
    # Retrieve the pending products associated with the current user
    pending_products = PendingProduct.objects.filter(user=request.user)
    return render(request, 'my_products.html', {'pending_products': pending_products})

@login_required
def edit_product(request, pk):
    # Retrieve the pending product to edit
    pending_product = get_object_or_404(PendingProduct, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=pending_product)
        if form.is_valid():
            # Check if a product with the same name already exists
            product_exists = Product.objects.filter(product_name=form.cleaned_data['product_name']).exists()
            api_product_exists = ApiProduct.objects.filter(product_name=form.cleaned_data['product_name']).exists()

            if product_exists or api_product_exists:
                messages.error(request, f'A product with the name "{form.cleaned_data["product_name"]}" already exists.')
                return render(request, 'create.html', {'form': form})  # Render the page with the form and error message
            else:
                form.save()
                return redirect('my_products')
    else:
        form = ProductForm(instance=pending_product)

    return render(request, 'edit_product.html', {'form': form})

@login_required
def delete_product(request, pk):
    # Retrieve the pending product to delete
    pending_product = get_object_or_404(PendingProduct, pk=pk)

    if request.method == 'POST':
        pending_product.delete()
        return redirect('my_products')

    return render(request, 'delete_product.html', {'pending_product': pending_product})


@login_required
def send_email_to_subscribers(request):
    if not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to access this page.")

    if request.method == 'POST':
        form = EmailSubscriberForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            subscribers = Subscriber.objects.all()

            recipient_list = [subscriber.email for subscriber in subscribers]

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
            
            messages.success(request, 'Email sent to subscribers successfully.')
            return redirect('index')
    else:
        form = EmailSubscriberForm()

    return render(request, 'send_email.html', {'form': form})


@login_required
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            user_email = request.user.email

            # Send email to exploresphereapp@gmail.com
            send_mail(
                subject,
                f"From: {user_email}\n\n{message}",
                user_email,
                ['exploresphereapp@gmail.com'],
                fail_silently=False,
            )

            messages.success(request, 'Your message has been sent successfully.')
            return redirect('contact')  # Redirect to the contact page or another page as needed
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})


@login_required
def newsletter_subscription(request):
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            # Save the subscription
            form.save_subscription(request.user)
            
            # Set the user's is_subscribed field to True
            request.user.is_subscribed = True
            request.user.save()
            
            # Generate the discount code
            discount_code = generate_discount_code()
            
            # Create a discount for the user with the generated code
            Discount.objects.create(
                user=request.user,
                code=discount_code,
                amount=10,  # Set the discount amount to 10
                used=False  # Mark the discount as unused initially
            )
            
            messages.success(request, 'Subscription successful. A discount has been generated for you.')
            return redirect('index')
    else:
        form = NewsletterSubscriptionForm()

    return render(request, 'index.html', {'form': form})

def generate_discount_code():
    # Generate 4 random upper case characters
    first_part = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    # Generate 4 random upper case characters
    second_part = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    # Generate 4 random upper case characters
    third_part = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    # Concatenate the parts with hyphens
    discount_code = f"{first_part}-{second_part}-{third_part}"
    
    return discount_code


@login_required
def checkout(request):
    if request.method == 'POST':
        # Get form data
        address = request.POST.get('address')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        city = request.POST.get('city')
        country = request.POST.get('country')
        zip_code = request.POST.get('zip_code')

        # Perform validation
        required_fields = [address, first_name, last_name, city, country, zip_code]
        if not all(required_fields):
            messages.error(request, "Please fill in all the required fields.")
            return redirect('checkout')

        # Get the basket for the current user
        basket, created = Basket.objects.get_or_create(user=request.user)

        # Check if the basket is empty
        if not basket.items.exists():
            messages.error(request, "Your basket is empty.")
            return redirect('checkout')

        # Calculate the total price of the order
        total_price = basket.items.aggregate(total_price=Sum('price'))['total_price'] or Decimal('0.00')

        # Fetch used discounts for the user
        used_discounts = Discount.objects.filter(user=request.user, used=True)

        # Calculate the total discount amount
        total_discount_amount = Decimal('0.00')
        for discount in used_discounts:
            total_discount_amount += total_price * (discount.amount / Decimal(100))

        # Calculate the total price after discounts
        total_price_after_discount = total_price - total_discount_amount

        # Send confirmation email
        subject = 'Order Confirmation'
        html_message = render_to_string('confirmation_email.html', {
            'address': address,
            'first_name': first_name,
            'last_name': last_name,
            'city': city,
            'country': country,
            'zip_code': zip_code,
            'total_price': total_price_after_discount,  # Use total price after discounts
            'basket_items': basket.items.all(),  # Include basket items in email
            'used_discounts': used_discounts,
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL  # Use the default from email defined in settings
        to_email = [request.user.email]
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)

        # Clear the basket after successful checkout
        basket.items.all().delete()

        # Delete all used discounts
        used_discounts.delete()

        messages.success(request, "Order successfully placed! You will receive a confirmation email.")
        return redirect('index')  # Redirect to home page after successful checkout

    return render(request, 'checkout.html')

def update_meal_product(request, meal_product_id):
    meal_product = get_object_or_404(MealProduct, id=meal_product_id)
    if request.method == 'POST':
        new_quantity = Decimal(request.POST.get('quantity_grams'))
        old_quantity = meal_product.quantity_grams  # Store the old quantity for calculation
        meal_product.quantity_grams = new_quantity
        meal_product.save()

        # Update meal totals
        meal = meal_product.meal
        meal.total_calories -= (meal_product.product.kcal_per_100g * old_quantity / 100)
        meal.total_proteins -= (meal_product.product.protein_per_100g * old_quantity / 100)
        meal.total_carbs -= (meal_product.product.carbs_per_100g * old_quantity / 100)
        meal.total_fats -= (meal_product.product.fats_per_100g * old_quantity / 100)
        meal.total_calories += (meal_product.product.kcal_per_100g * new_quantity / 100)
        meal.total_proteins += (meal_product.product.protein_per_100g * new_quantity / 100)
        meal.total_carbs += (meal_product.product.carbs_per_100g * new_quantity / 100)
        meal.total_fats += (meal_product.product.fats_per_100g * new_quantity / 100)
        meal.save()

        return redirect('meal_detail', meal_id=meal_product.meal.id)
    return render(request, 'update_meal_product.html', {'meal_product': meal_product})


def delete_meal_product(request, meal_product_id):
    meal_product = get_object_or_404(MealProduct, id=meal_product_id)
    if request.method == 'POST':
        meal_id = meal_product.meal.id
        old_quantity = meal_product.quantity_grams  # Store the old quantity for calculation
        meal_product.delete()

        # Update meal totals
        meal = Meal.objects.get(pk=meal_id)
        meal.total_calories -= (meal_product.product.kcal_per_100g * old_quantity / 100)
        meal.total_proteins -= (meal_product.product.protein_per_100g * old_quantity / 100)
        meal.total_carbs -= (meal_product.product.carbs_per_100g * old_quantity / 100)
        meal.total_fats -= (meal_product.product.fats_per_100g * old_quantity / 100)

        # Ensure meal total nutritional data doesn't go negative
        meal.total_calories = max(meal.total_calories, 0)
        meal.total_proteins = max(meal.total_proteins, 0)
        meal.total_carbs = max(meal.total_carbs, 0)
        meal.total_fats = max(meal.total_fats, 0)

        meal.save()

        # Delete the meal if it becomes empty
        if meal.mealproduct_set.count() == 0 and meal.mealapiproduct_set.count() == 0:
            meal.delete()
            return redirect('calculator')

        return redirect('meal_detail', meal_id=meal_id)

    raise Http404("Invalid request method")

def update_meal_api_product(request, meal_api_product_id):
    meal_api_product = get_object_or_404(MealApiProduct, id=meal_api_product_id)
    if request.method == 'POST':
        new_quantity = Decimal(request.POST.get('quantity_grams'))
        old_quantity = meal_api_product.quantity_grams  # Store the old quantity for calculation
        meal_api_product.quantity_grams = new_quantity
        meal_api_product.save()

        # Update meal totals
        meal = meal_api_product.meal
        meal.total_calories -= (meal_api_product.kcal_per_100g * old_quantity / 100)
        meal.total_proteins -= (meal_api_product.protein_per_100g * old_quantity / 100)
        meal.total_carbs -= (meal_api_product.carbs_per_100g * old_quantity / 100)
        meal.total_fats -= (meal_api_product.fats_per_100g * old_quantity / 100)
        meal.total_calories += (meal_api_product.kcal_per_100g * new_quantity / 100)
        meal.total_proteins += (meal_api_product.protein_per_100g * new_quantity / 100)
        meal.total_carbs += (meal_api_product.carbs_per_100g * new_quantity / 100)
        meal.total_fats += (meal_api_product.fats_per_100g * new_quantity / 100)
        meal.save()

        return redirect('meal_detail', meal_id=meal_api_product.meal.id)
    return render(request, 'update_meal_api_product.html', {'meal_api_product': meal_api_product})

def delete_meal_api_product(request, meal_api_product_id):
    meal_api_product = get_object_or_404(MealApiProduct, id=meal_api_product_id)
    if request.method == 'POST':
        meal_id = meal_api_product.meal.id
        old_quantity = meal_api_product.quantity_grams  # Store the old quantity for calculation
        meal_api_product.delete()

        # Update meal totals
        meal = Meal.objects.get(pk=meal_id)
        meal.total_calories -= (meal_api_product.kcal_per_100g * old_quantity / 100)
        meal.total_proteins -= (meal_api_product.protein_per_100g * old_quantity / 100)
        meal.total_carbs -= (meal_api_product.carbs_per_100g * old_quantity / 100)
        meal.total_fats -= (meal_api_product.fats_per_100g * old_quantity / 100)

        # Ensure meal total nutritional data doesn't go negative
        meal.total_calories = max(meal.total_calories, 0)
        meal.total_proteins = max(meal.total_proteins, 0)
        meal.total_carbs = max(meal.total_carbs, 0)
        meal.total_fats = max(meal.total_fats, 0)

        meal.save()

        # Delete the meal if it becomes empty
        if meal.mealproduct_set.count() == 0 and meal.mealapiproduct_set.count() == 0:
            meal.delete()
            return redirect('calculator')

        return redirect('meal_detail', meal_id=meal_id)
    raise Http404("Invalid request method")

def meal_detail(request, meal_id):
    meal = get_object_or_404(Meal, pk=meal_id)
    context = {'meal': meal}
    return render(request, 'meal_detail.html', context)

@login_required
def calculator(request):
    user = request.user
    try:
        user_profile = user.userprofile
    except UserProfile.DoesNotExist:
        # If user doesn't have a profile, redirect them to create one
        return redirect('create_profile')

    # Calculate Basal Metabolic Rate (BMR) based on gender
    if user_profile.gender == 'male':
        bmr = 88.362 + (13.397 * float(user_profile.weight)) + (4.799 * float(user_profile.height)) - (5.677 * float(user_profile.age))
    else:  # Female
        bmr = 447.593 + (9.247 * float(user_profile.weight)) + (3.098 * float(user_profile.height)) - (4.330 * float(user_profile.age))

    # Adjust BMR based on activity level
    activity_levels = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    adjusted_bmr = bmr * activity_levels[user_profile.activity_level]

    # Adjust BMR based on goal
    if user_profile.goal == 'cut':
        daily_calories = adjusted_bmr - 500  # Deficit of 500 calories per day for cutting
    elif user_profile.goal == 'bulk':
        daily_calories = adjusted_bmr + 500  # Surplus of 500 calories per day for bulking
    else:  # Maintain
        daily_calories = adjusted_bmr  # Maintain current weight

    user_profile.daily_calories = daily_calories
    user_profile.save()

    # Fetch meal objects for each meal type and calculate total nutritional data
    breakfast = Meal.objects.filter(meal_type='Breakfast', user=user).first()
    lunch = Meal.objects.filter(meal_type='Lunch', user=user).first()
    dinner = Meal.objects.filter(meal_type='Dinner', user=user).first()
    snacks = Meal.objects.filter(meal_type='Snacks', user=user).first()

    # Query for each type of meal separately based on the user's products
    breakfast_products = MealProduct.objects.filter(meal__meal_type='Breakfast', meal__user=user)
    lunch_products = MealProduct.objects.filter(meal__meal_type='Lunch', meal__user=user)
    dinner_products = MealProduct.objects.filter(meal__meal_type='Dinner', meal__user=user)
    snacks_products = MealProduct.objects.filter(meal__meal_type='Snacks', meal__user=user)

    breakfast_api_products = MealApiProduct.objects.filter(meal__meal_type='Breakfast', meal__user=user)
    lunch_api_products = MealApiProduct.objects.filter(meal__meal_type='Lunch', meal__user=user)
    dinner_api_products = MealApiProduct.objects.filter(meal__meal_type='Dinner', meal__user=user)
    snacks_api_products = MealApiProduct.objects.filter(meal__meal_type='Snacks', meal__user=user)

    # Calculate total nutritional data for each meal
    breakfast_total = calculate_total_nutritional_data(breakfast, breakfast_products, breakfast_api_products)
    lunch_total = calculate_total_nutritional_data(lunch, lunch_products, lunch_api_products)
    dinner_total = calculate_total_nutritional_data(dinner, dinner_products, dinner_api_products)
    snacks_total = calculate_total_nutritional_data(snacks, snacks_products, snacks_api_products)

    # Calculate total nutritional data for all meals
    total_all_meals = {
        'total_calories': breakfast_total['total_calories'] + lunch_total['total_calories'] +
                          dinner_total['total_calories'] + snacks_total['total_calories'],
        'total_proteins': breakfast_total['total_proteins'] + lunch_total['total_proteins'] +
                          dinner_total['total_proteins'] + snacks_total['total_proteins'],
        'total_carbs': breakfast_total['total_carbs'] + lunch_total['total_carbs'] +
                       dinner_total['total_carbs'] + snacks_total['total_carbs'],
        'total_fats': breakfast_total['total_fats'] + lunch_total['total_fats'] +
                      dinner_total['total_fats'] + snacks_total['total_fats']
    }
    calories_class = 'neutral'
    if user_profile.goal == 'cut':
     if total_all_meals['total_calories'] < user_profile.daily_calories:
        calories_class = 'good'
     else:
        calories_class = 'bad'
    elif user_profile.goal == 'bulk':
     if total_all_meals['total_calories'] > user_profile.daily_calories:
        calories_class = 'good'
     else:
        calories_class = 'bad'
    context = {
        'breakfast': breakfast,
        'lunch': lunch,
        'dinner': dinner,
        'snacks': snacks,
        'breakfast_products': breakfast_products,
        'lunch_products': lunch_products,
        'dinner_products': dinner_products,
        'snacks_products': snacks_products,
        'breakfast_api_products': breakfast_api_products,
        'lunch_api_products': lunch_api_products,
        'dinner_api_products': dinner_api_products,
        'snacks_api_products': snacks_api_products,
        'breakfast_total': breakfast_total,
        'lunch_total': lunch_total,
        'dinner_total': dinner_total,
        'snacks_total': snacks_total,
        'total_all_meals': total_all_meals,
        'daily_calories': daily_calories,
        'calories_class': calories_class,
    }
    print("Calories class:", calories_class)
    return render(request, 'calculator.html', context)


@login_required
def create_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()
            messages.success(request, 'User profile created successfully.')
            return redirect('calculator')
    else:
        form = UserProfileForm()
    
    return render(request, 'create_profile.html', {'form': form})

def calculate_total_nutritional_data(meal, meal_products, meal_api_products):
    total_calories = sum((product.product.kcal_per_100g * product.quantity_grams / 100) for product in meal_products)
    total_proteins = sum((product.product.protein_per_100g * product.quantity_grams / 100) for product in meal_products)
    total_carbs = sum((product.product.carbs_per_100g * product.quantity_grams / 100) for product in meal_products)
    total_fats = sum((product.product.fats_per_100g * product.quantity_grams / 100) for product in meal_products)

    total_calories += sum((api_product.kcal_per_100g * api_product.quantity_grams / 100) for api_product in meal_api_products)
    total_proteins += sum((api_product.protein_per_100g * api_product.quantity_grams / 100) for api_product in meal_api_products)
    total_carbs += sum((api_product.carbs_per_100g * api_product.quantity_grams / 100) for api_product in meal_api_products)
    total_fats += sum((api_product.fats_per_100g * api_product.quantity_grams / 100) for api_product in meal_api_products)

    return {
        'total_calories': total_calories,
        'total_proteins': total_proteins,
        'total_carbs': total_carbs,
        'total_fats': total_fats,
    }

@login_required
def add_to_meal(request, meal_type):
    user = request.user
    search_query = request.POST.get('product_name', '')
    search_results = []

    if search_query.strip():
        # Perform the search
        search_results = search_product(search_query, user=user)
        for product in search_results:
                if isinstance(product, Product):
                    product.source = 'database'
                elif isinstance(product, ApiProduct):
                    product.source = 'api'
                else:
                    # Handle other cases if needed
                   pass
    if 'add_to_meal' in request.POST:
        product_id = request.POST.get('add_to_meal')
        quantity = request.POST.get(f'quantity_{product_id}')

        if product_id and quantity:
            try:
                product = Product.objects.get(pk=product_id)
                meal, created = Meal.objects.get_or_create(meal_type=meal_type, user=user)
                meal_product = meal.add_product(product, quantity)  # Modify this line
                if meal_product:
                    messages.success(request, "Product added to meal successfully.")
                else:
                    messages.info(request, "Product already exists in the meal.")
                return redirect('add_to_meal', meal_type=meal_type)
            except Product.DoesNotExist:
                try:
                    api_product = ApiProduct.objects.get(pk=product_id)
                    meal, created = Meal.objects.get_or_create(meal_type=meal_type, user=user)
                    meal_api_product = meal.add_product(api_product, quantity)  # Modify this line
                    if meal_api_product:
                        messages.success(request, "API Product added to meal successfully.")
                    else:
                        messages.info(request, "API Product already exists in the meal.")
                    return redirect('add_to_meal', meal_type=meal_type)
                except ApiProduct.DoesNotExist:
                    messages.error(request, "Product not found.")
                    return redirect('add_to_meal', meal_type=meal_type)
        else:
            messages.error(request, "Please provide both a product and a quantity.")
            return redirect('add_to_meal', meal_type=meal_type)

    context = {'meal_type': meal_type, 'search_results': search_results, 'search_query': search_query}
    return render(request, 'add_to_meal.html', context)

@login_required
def myprofile(request):
    user = request.user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user.userprofile)  # Use the userprofile instance
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('myprofile')  # Redirect to the profile page or any other desired URL
    else:
        form = UserProfileForm(instance=user.userprofile)  # Use the userprofile instance

    return render(request, 'myprofile.html', {'form': form})


@login_required
def user_discounts(request):
    user_discounts = Discount.objects.filter(user=request.user)
    return render(request, 'user_discounts.html', {'user_discounts': user_discounts})

@login_required
def apply_discount(request):
    if request.method == 'POST':
        discount_code = request.POST.get('discount_code')
        try:
            discount = Discount.objects.get(code=discount_code, user=request.user, used=False)

            # Apply the discount
            if not discount.used:

                discount.used = True
                discount.save()
                messages.success(request, 'Discount applied successfully.')
            else:
                messages.error(request, 'Discount already used.')
        except Discount.DoesNotExist:
            messages.error(request, 'Invalid discount code.')

    return redirect('basket_page')

@login_required
def remove_discount(request, discount_id):
    discount = get_object_or_404(Discount, id=discount_id, user=request.user, used=True)
    discount.used = False
    discount.save()
    return redirect('basket_page')


def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)

    # Check if the current user is either the author of the comment or the author of the post
    if request.user == comment.user or (comment.post.user and request.user == comment.post.user):
        # Delete the comment
        comment.delete()

    # Redirect to the same post page after deleting the comment
    return redirect('post', post_id=comment.post.id)


@login_required
def create_post(request):
    # Check if the user is banned
    try:
        banned = Banned.objects.get(user=request.user)
        if banned.banned_until and banned.banned_until > timezone.now():
            # User is banned, redirect to a page informing about the ban duration
            banned_until = banned.banned_until.strftime("%Y-%m-%d %H:%M:%S")
            messages.error(request, f'You are banned until {banned_until}.')
            return redirect('banned_info')  # Change 'banned_info' to the URL name of the page with ban information
        else:
            # If the ban duration has passed, delete the Banned model
            banned.delete()
    except Banned.DoesNotExist:
        pass  # User is not banned or there is no ban record
    
    # Continue with the post creation logic
    products = Product.objects.all().order_by('product_name')
    api_products = ApiProduct.objects.all().order_by('product_name')

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            product_type = form.cleaned_data.get('product_type')
            content = form.cleaned_data.get('content')
            title = form.cleaned_data.get('title')

            # Ensure the current user is associated with the post
            user = request.user

            post = Post(content=content, title=title, user=user, product_type=product_type)

            # Set the appropriate product instance based on the product type
            if product_type == 'Product':
                product_instance_id = form.cleaned_data.get('object_id')
                try:
                    product_instance = Product.objects.get(id=product_instance_id)
                    post.product = product_instance
                    post.product_name = product_instance.product_name  # Set the product_name attribute
                except Product.DoesNotExist:
                    return render(request, 'create_post.html', {'form': form, 'products': products, 'api_products': api_products, 'error_message': 'Selected product does not exist'})
            elif product_type == 'ApiProduct':
                api_product_instance_id = form.cleaned_data.get('object_id')
                try:
                    api_product_instance = ApiProduct.objects.get(id=api_product_instance_id)
                    post.product = api_product_instance
                    post.product_name = api_product_instance.product_name  # Set the product_name attribute
                except ApiProduct.DoesNotExist:
                    return render(request, 'create_post.html', {'form': form, 'products': products, 'api_products': api_products, 'error_message': 'Selected API product does not exist'})

            post.save()

            return redirect('index')
    else:
        # If it's a GET request, initialize the form and set the choices based on the initial product_type
        initial_product_type = request.GET.get('product_type', 'Product')  # Default to 'Product' if not provided
        form = PostForm(initial={'product_type': initial_product_type})
        form.set_product_choices(initial_product_type)  # Set the initial choices for the object_id field

    return render(request, 'create_post.html', {'form': form, 'products': products, 'api_products': api_products})

@login_required
def post_list(request):
    posts = Post.objects.all()
    return render(request, 'post_list.html', {'posts': posts})

def post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = Comment.objects.filter(post=post).order_by('-pub_date')

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            # Save the comment
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()

            messages.success(request, 'Comment submitted successfully.')
            # Redirect to the same post page after submitting the comment
            return redirect('post', post_id=post_id)
    else:
        comment_form = CommentForm()

    return render(request, 'post.html', {'post': post, 'comment_form': comment_form, 'comments': comments})


def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)

    # Check if the current user is the author of the comment
    if request.user != comment.user:
        # If the current user is not the author, redirect to some other page or show an error message
        return redirect('some_other_page')  # Replace 'some_other_page' with the URL name or path of your choice

    if request.method == 'POST':
        # Update the comment content with the data from the form
        comment.content = request.POST.get('content')
        comment.save()
        # Redirect back to the post page after editing the comment
        return redirect('post', post_id=comment.post.id)

    # If the request method is not POST, simply render the same page
    # You can handle GET requests differently if needed

    return redirect('post', post_id=comment.post.id)  # Redirect back to the post page if not a POST request


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    products = Product.objects.all()
    api_products = ApiProduct.objects.all()

    # Check if the current user is the author of the post
    if request.user != post.user:
        messages.error(request, "You do not have permission to edit this post.")
        return redirect('post', post_id=post_id)

    if request.method == 'POST':
        # If the form is submitted, update the post with the new data
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            # Save the form data without committing to the database
            updated_post = form.save(commit=False)

            # Set the user who originally wrote the post
            updated_post.user = request.user

            # Set the appropriate product instance based on the product type
            product_type = form.cleaned_data.get('product_type')
            if product_type == 'Product':
                product_instance_id = form.cleaned_data.get('object_id')
                try:
                    product_instance = Product.objects.get(id=product_instance_id)
                    updated_post.product = product_instance
                    updated_post.product_name = product_instance.product_name
                except Product.DoesNotExist:
                    return render(request, 'edit_post.html', {'form': form, 'products': products, 'api_products': api_products, 'error_message': 'Selected product does not exist'})
            elif product_type == 'ApiProduct':
                api_product_instance_id = form.cleaned_data.get('object_id')
                try:
                    api_product_instance = ApiProduct.objects.get(id=api_product_instance_id)
                    updated_post.product = api_product_instance
                    updated_post.product_name = api_product_instance.product_name
                except ApiProduct.DoesNotExist:
                    return render(request, 'edit_post.html', {'form': form, 'products': products, 'api_products': api_products, 'error_message': 'Selected API product does not exist'})

            # Save the updated post with the modified product name and user
            updated_post.save()

            messages.success(request, "Post updated successfully.")
            return redirect('my_posts')
    else:
        # If it's a GET request, initialize the form with the current post data
        form = PostForm(instance=post)
    
    return render(request, 'edit_post.html', {'form': form, 'products': products, 'api_products': api_products})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    # Check if the current user is the author of the post
    if request.user != post.user:
        messages.error(request, "You do not have permission to delete this post.")
        return redirect('post', post_id=post_id)

    if request.method == 'POST':
        # If the form is submitted, delete the post
        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect('my_posts')
    else:
        # If it's a GET request, confirm the deletion
        return render(request, 'confirm_delete_post.html', {'post': post})
    

@login_required
def my_posts(request):
    posts = Post.objects.filter(user=request.user)

    for post in posts:
        post.editable = False
        if request.user == post.user:
            post.editable = True

    return render(request, 'my_posts.html', {'posts': posts})

@login_required
def manage_delete(request, post_id):
    if request.method == 'POST' and request.user.is_superuser:
        try:
            post = Post.objects.get(id=post_id)
            post.delete()
            messages.success(request, 'Post deleted successfully.')
        except Post.DoesNotExist:
            messages.error(request, 'Post does not exist.')
    return redirect('post_list')

@login_required
def manage_ban(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST' and request.user.is_superuser:
        try:
            ban_duration_minutes = int(request.POST.get('ban_duration', 2))  # Default ban duration is 2 minutes
            ban_end_date = timezone.now() + timedelta(minutes=ban_duration_minutes)
            banned, created = Banned.objects.get_or_create(user=user)
            banned.banned_until = ban_end_date
            banned.save()
            messages.success(request, f'User {user.name} has been banned until {ban_end_date}.')
        except User.DoesNotExist:
            messages.error(request, 'User does not exist.')
    return redirect('post_list')

def banned_info(request):
    try:
        banned = Banned.objects.get(user=request.user)
        banned_until = banned.banned_until.strftime("%H:%M:%S %d.%m.%Y")
    except Banned.DoesNotExist:
        banned_until = None

    return render(request, 'banned_info.html', {'banned_until': banned_until})
