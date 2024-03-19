from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth import authenticate, login, logout
from .models import Product, ApiProduct, Allergy, Basket, BasketItem, ProductRating, ApiProductRating, UserProfile, Discount
from .forms import RegistrationForm, LoginForm, UserProfileForm
import requests
from decimal import Decimal
import json
from django.contrib.auth.decorators import user_passes_test
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
from .forms import PostForm, EmailSubscriberForm, ContactForm, NewsletterSubscriptionForm, CustomPasswordChangeForm, CommentForm, RecipeForm
from .models import Post, Comment, User
from itertools import chain
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Meal, MealProduct, MealApiProduct, Banned, Recipe, Ingredient
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
from django.db.models import Q
from django.http import JsonResponse
import time

@login_required
def index(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name', '')
        if product_name.strip():  
            product_info = search_product(product_name, user=request.user)
            
            for product in product_info:
                if isinstance(product, Product):
                    product.source = 'database'
                elif isinstance(product, ApiProduct):
                    product.source = 'api'
                else:
                    
                    pass
            return render(request, 'index.html', {'search_query': product_name, 'search_results': product_info})
        else:  
            best_rated_products = Product.objects.filter(user_rating__isnull=False).order_by('-user_rating')[:4]
            cheapest_products = Product.objects.filter(price__gt=0).order_by('price')[:4]
            return render(request, 'index.html', {'best_rated_products': best_rated_products, 'cheapest_products': cheapest_products})
    else:
        
        best_rated_products = sorted(
            chain(Product.objects.filter(user_rating__isnull=False), ApiProduct.objects.filter(user_rating__isnull=False)),
            key=lambda x: x.user_rating if x.user_rating else float('-inf'),
            reverse=True
        )[:4]
        
        
        cheapest_products = sorted(
            chain(Product.objects.filter(price__gt=0), ApiProduct.objects.filter(price__gt=0)),
            key=lambda x: x.price
        )[:4]
        user_diet = request.user.diet.lower()
        suggested_products = []
        if user_diet == 'vegan':
            suggested_products = chain(Product.objects.filter(is_vegan=True), ApiProduct.objects.filter(is_vegan=True))
        elif user_diet == 'vegetarian':
            suggested_products = chain(Product.objects.filter(is_vegetarian=True), ApiProduct.objects.filter(is_vegetarian=True))
        elif user_diet == 'low fat':
            suggested_products = chain(Product.objects.filter(fats_per_100g__lte=10),
                               ApiProduct.objects.filter(fats_per_100g__lte=10))
        elif user_diet == 'high protein':
            suggested_products = chain(Product.objects.filter(protein_per_100g__gte=15),
                               ApiProduct.objects.filter(protein_per_100g__gte=15))
        elif user_diet == 'keto':
            suggested_products = chain(Product.objects.filter(fats_per_100g__gte=25, carbs_per_100g__lte=5),
                               ApiProduct.objects.filter(fats_per_100g__gte=25, carbs_per_100g__lte=5))
            
        suggested_products = list(suggested_products)[:4]
        
        for product in chain(best_rated_products, cheapest_products, suggested_products):
            if isinstance(product, Product):
                product.source = 'database'
            elif isinstance(product, ApiProduct):
                product.source = 'api'
            else:       
                pass

        return render(request, 'index.html', {'best_rated_products': best_rated_products, 
                                               'cheapest_products': cheapest_products, 
                                               'suggested_products': suggested_products})
    

def registration_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            response_token = request.POST.get('g-recaptcha-response', '')
            if verify_recaptcha(response_token):
                user = form.save(commit=False)
                user.save()
                form.save_m2m()
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, 'reCAPTCHA verification failed. Please try again.')
        else:
            # Check for specific error messages
            if 'email' in form.errors:
                messages.error(request, 'Email already exists. Please choose a different one.')
            elif 'name' in form.errors:
                messages.error(request, 'Username already taken. Please choose a different one.')
            else:
                messages.error(request, 'Invalid form submission. Please correct the errors.')
    else:
        form = RegistrationForm()
    return render(request, 'register.html',{'form':form })

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
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
    secret_key = '6Le2Qn4pAAAAAPMo61FnEEKdFKApauuRG9dh0Hrt'  
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

            
            if password_change_form.is_valid():
                password_change_form.save()
                messages.success(request, 'Password updated successfully.')

            return redirect('myaccount')  

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

def search_product_by_barcode(request, barcode):
    if request.method == 'GET':
        if barcode:
            # Search in ApiProduct model
            api_product = ApiProduct.objects.filter(ean_code=barcode).first()
            if api_product:
                return redirect(reverse('product_detail', kwargs={'product_id': api_product.id, 'source': 'api'}))
            else:
                # Search in Product model
                product = Product.objects.filter(ean_code=barcode).first()
                if product:
                    return redirect(reverse('product_detail', kwargs={'product_id': product.id, 'source': 'database'}))
                else:
                    # Restart the barcode detection process after 15 seconds
                    time.sleep(35)
                    return redirect('/barcode_scanner/')  # Adjust the URL to your barcode scanning page
        else:
            return JsonResponse({'status': 'error', 'message': 'Barcode parameter missing'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


def search_product(product_name, user=None):
    # Fetch products from the local database
    database_products = Product.objects.filter(product_name__icontains=product_name)

    # Initialize list for API products
    api_products = []

    # Fetch user allergies if user is authenticated
    user_allergies = None
    if user and user.is_authenticated:
        user_allergies = user.allergies.all()

    # Fetch products from the Open Food Facts API
    api_url = f'https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1'
    response = requests.get(api_url)

    if response.status_code == 200:
        product_data = response.json()
        if 'products' in product_data:
            for product in product_data['products']:
                # Check if product has a valid name
                name = product.get('product_name', '')
                if not name:
                    continue  # Skip this product if it has no name
                
                # Extract product details
                brands = product.get('brands', '')
                quantity = product.get('quantity', '')
                categories = product.get('categories', '')
                ean_code = product.get('code', '') 
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
                ingredients = product.get('ingredients', {})
                is_vegan = all(ingredient.get('vegan', '') == 'yes' if 'vegan' in ingredient else True for ingredient in ingredients)
                is_vegetarian = all(ingredient.get('vegetarian', '') == 'yes' if 'vegetarian' in ingredient else True for ingredient in ingredients)
                if nutriscore_grade is not None:
                    nutriscore_grade = nutriscore_grade.upper()

                # Create or retrieve ApiProduct instance
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
                        'allergies': json.dumps(allergies) if allergies else None,
                        'is_vegan': is_vegan,
                        'is_vegetarian': is_vegetarian,
                        'ean_code': ean_code  # Save EAN code to the model
                    }
                )

                # Retrieve user rating
                rating = None
                try:
                    api_product = ApiProduct.objects.get(product_name=name)
                    rating = api_product.user_rating
                except ApiProduct.DoesNotExist:
                    pass  # No need to handle if product doesn't exist

                # Update user rating
                api_product.user_rating = rating

                # Append to list of API products
                api_products.append(api_product)

                # Download and save image if available
                if product.get('image_url') and not api_product.image:
                    image_url = product.get('image_url')
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        api_product.image.save(f'{name}_image.jpg', ContentFile(response.content), save=True)

    # Merge database and API products
    all_products = list(database_products) + api_products

    # Filter out duplicates based on product name
    unique_products = {product.product_name: product for product in all_products}

    # Return unique products
    return unique_products.values()

def rate_product(request, product_id, source):
    if request.method == 'POST':
        try:
            rating_value = Decimal(request.POST.get('rating'))  
        except ValueError:
            return HttpResponseBadRequest("Invalid rating")

        if rating_value < 0 or rating_value > 10:  
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

            
            rating, created = rating_model.objects.get_or_create(user=request.user, product=product)

            
            rating.rating = rating_value
            rating.save()

            
            product.calculate_average_rating()

            
            product_allergies = json.loads(product.allergies) if product.allergies else []
            user_allergies = request.user.allergies.all() if request.user.is_authenticated else []
            common_allergies = set(product_allergies) & set(allergy.name for allergy in user_allergies)

            
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

        
        if source == 'database':
            product_allergies = []
            if product.allergies:
                product_allergies = product.allergies.split(',')  
        elif source == 'api':
            product_allergies = []
            if product.allergies:
                product_allergies = json.loads(product.allergies)

        
        user_allergies = []
        if request.user.is_authenticated:
            user_allergies = request.user.allergies.all()

        
        common_allergies = set(product_allergies) & set(allergy.name for allergy in user_allergies)

        
        product_rating = getattr(product, 'user_rating', None)

        return render(request, 'product_detail.html', {'product': product, 'common_allergies': common_allergies, 'product_rating': product_rating, 'source': source})
    except product_model.DoesNotExist:
        return HttpResponseBadRequest("Product not found")

@login_required
def add_to_basket(request, product_id, source):
    if request.method == 'POST':
        
        if source not in ['database', 'api']:
            return HttpResponseBadRequest("Invalid source")

        
        if source == 'database':
            product_model = Product
        elif source == 'api':
            product_model = ApiProduct

        
        product = get_object_or_404(product_model, pk=product_id)

        
        basket, created = Basket.objects.get_or_create(user=request.user)

        
        if source == 'database':
            existing_item = basket.items.filter(product=product, api_product=None)
        elif source == 'api':
            existing_item = basket.items.filter(api_product=product, product=None)

        if existing_item.exists():
            
            existing_item.update(quantity=F('quantity') + 1)
        else:
            
            if source == 'database':
                BasketItem.objects.create(basket=basket, product=product, source=source)
            elif source == 'api':
                BasketItem.objects.create(basket=basket, api_product=product, source=source, quantity=1)

        return redirect('basket_page')  

    
    return HttpResponseBadRequest("Invalid request method")

@login_required
def increment_quantity(request, product_id, source):
    try:
        
        if source == 'database':
            basket_item = BasketItem.objects.get(product_id=product_id, source=source, basket__user=request.user)
        elif source == 'api':
            basket_item = BasketItem.objects.get(api_product_id=product_id, source=source, basket__user=request.user)

        if basket_item.quantity < 20:  
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
    
    basket, created = Basket.objects.get_or_create(user=request.user)

    
    items = basket.items.select_related('product', 'api_product')

    total_price = Decimal('0.00')  

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

            
            if product.price is not None:
                total_price += Decimal(product.price) * quantity

            if product.nutriscore:
                
                health_rating_contribution = calculate_health_rating(product.nutriscore) * quantity
                total_health_rating += health_rating_contribution
                products_in_basket.append({'product': product, 'source': source, 'quantity': quantity})

    
    used_discounts = Discount.objects.filter(user=request.user, used=True)

    
    total_discount_amount = Decimal('0.00')
    for discount in used_discounts:
        total_discount_amount += total_price * (discount.amount / Decimal(100))

    total_price_after_discount = total_price - total_discount_amount
    savings = total_price - total_price_after_discount

    if not products_in_basket:  
        return render(request, 'basket_empty.html')

    
    if total_quantity > 0:
        average_health_rating = total_health_rating / total_quantity
    else:
        average_health_rating = Decimal('0.00')

    
    average_health_rating_mapped = map_health_rating(average_health_rating)

    
    return render(request, 'basket.html', {'products_in_basket': products_in_basket, 'total_price': total_price,
                                            'total_price_after_discount': total_price_after_discount, 'savings': savings,
                                            'used_discounts': used_discounts, 'average_health_rating': average_health_rating_mapped})

def calculate_health_rating(nutriscore):
    
    health_rating_map = {
        'A': Decimal('0.9'),
        'B': Decimal('0.7'),
        'C': Decimal('0.5'),
        'D': Decimal('0.3'),
        'E': Decimal('0.1'),
    }

    return health_rating_map.get(nutriscore, Decimal('0.1'))  

def map_health_rating(health_rating):
    
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
        
        if source not in ['database', 'api']:
            return JsonResponse({'error': 'Invalid source'}, status=400)

        
        basket_item = BasketItem.objects.filter(
            basket__user=request.user,
            source=source,
            product_id=product_id if source == 'database' else None,
            api_product_id=product_id if source == 'api' else None
        ).first()

        if basket_item:
            basket_item.delete()
            return redirect('basket_page')  
        else:
            return JsonResponse({'error': 'Item not found'}, status=404)

    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user  
            
            
            existing_pending_product = PendingProduct.objects.filter(
                product_name=form.cleaned_data['product_name'],
                user=user
            ).exists()
            
            if existing_pending_product:
                messages.error(request, f'A pending product with the name "{form.cleaned_data["product_name"]}" already exists.')
                return render(request, 'create.html', {'form': form})  
            
            product = form.save(commit=False)
            product.user = user
            product.save()  
            
            
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
                
                last_appended_product = existing_pending_products.last()
                
                approved_product = last_appended_product.handle_similar_products()
                if approved_product:
                    approved_product.approved = True  
                    approved_product.save()
                    
                    last_appended_product.delete()
            elif existing_pending_products.count() >= 4:
                
                last_appended_product = existing_pending_products.last()
                existing_pending_products.exclude(id=last_appended_product.id).delete()
                
                pending_product = last_appended_product
                product = Product.objects.create(
                    product_name=pending_product.product_name,
                    brands=pending_product.brands,
                    quantity=pending_product.quantity,
                    categories=pending_product.categories,
                    protein_per_100g=pending_product.protein_per_100g,
                    carbs_per_100g=pending_product.carbs_per_100g,
                    fats_per_100g=pending_product.fats_per_100g,
                    sugars_per_100g=pending_product.sugars_per_100g,  
                    sodium_per_100g=pending_product.sodium_per_100g,  
                    saturated_fats_per_100g=pending_product.saturated_fats_per_100g,  
                    kcal_per_100g=pending_product.kcal_per_100g,
                    price=pending_product.price,
                    product_type=pending_product.product_type,
                    user_rating=pending_product.user_rating,
                    allergies=pending_product.allergies,
                    approved=True, 
                    image=pending_product.image,
                    is_vegan=pending_product.is_vegan,
                    is_vegetarian=pending_product.is_vegetarian,
                    ean_code=pending_product.ean_code
                )
                
                last_appended_product.delete()
            else:
                
                product.save()
                
            return redirect('product_created') 
    else:
        form = ProductForm()

    return render(request, 'create.html', {'form': form})

@login_required
def product_created(request):
    
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
            
            product = pending_approval.approve()
            
            product.image = pending_approval.image
            product.is_vegan = pending_approval.is_vegan
            product.is_vegetarian = pending_approval.is_vegetarian
            product.ean_code=pending_approval.ean_code
            product.save()
        
        
        pending_products.filter(id__in=approved_products).delete()

        return redirect('pending_products') 

    return render(request, 'pending_products.html', {'pending_products': pending_products})

def pending_products(request):
    pending_products = PendingProduct.objects.all()  
    return render(request, 'pending_products.html', {'pending_products': pending_products})

@login_required
def my_products(request):
    
    pending_products = PendingProduct.objects.filter(user=request.user)
    return render(request, 'my_products.html', {'pending_products': pending_products})

@login_required
def edit_product(request, pk):
    
    pending_product = get_object_or_404(PendingProduct, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=pending_product)
        if form.is_valid():
            
            product_exists = Product.objects.filter(product_name=form.cleaned_data['product_name']).exists()
            api_product_exists = ApiProduct.objects.filter(product_name=form.cleaned_data['product_name']).exists()

            if product_exists or api_product_exists:
                messages.error(request, f'A product with the name "{form.cleaned_data["product_name"]}" already exists.')
                return render(request, 'create.html', {'form': form})  
            else:
                form.save()
                return redirect('my_products')
    else:
        form = ProductForm(instance=pending_product)

    return render(request, 'edit_product.html', {'form': form})

@login_required
def delete_product(request, pk):
    
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

            
            send_mail(
                subject,
                f"From: {user_email}\n\n{message}",
                user_email,
                ['exploresphereapp@gmail.com'],
                fail_silently=False,
            )
            return redirect('contact')  
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})


@login_required
def newsletter_subscription(request):
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            
            form.save_subscription(request.user)
            
            
            request.user.is_subscribed = True
            request.user.save()
            
            
            discount_code = generate_discount_code()
            
            
            Discount.objects.create(
                user=request.user,
                code=discount_code,
                amount=10,  
                used=False  
            )
            
            messages.success(request, 'Subscription successful. A discount has been generated for you.')
            return redirect('index')
    else:
        form = NewsletterSubscriptionForm()

    return render(request, 'index.html', {'form': form})

def generate_discount_code():
    
    first_part = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    
    second_part = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    
    third_part = ''.join(random.choices(string.ascii_uppercase, k=4))
    
    
    discount_code = f"{first_part}-{second_part}-{third_part}"
    
    return discount_code


@login_required
def checkout(request):
    if request.method == 'POST':
        
        address = request.POST.get('address')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        city = request.POST.get('city')
        country = request.POST.get('country')
        zip_code = request.POST.get('zip_code')

        
        required_fields = [address, first_name, last_name, city, country, zip_code]
        if not all(required_fields):
            messages.error(request, "Please fill in all the required fields.")
            return redirect('checkout')

        
        basket, created = Basket.objects.get_or_create(user=request.user)

        
        if not basket.items.exists():
            messages.error(request, "Your basket is empty.")
            return redirect('checkout')

        
        total_price = basket.items.aggregate(total_price=Sum('price'))['total_price'] or Decimal('0.00')

        
        used_discounts = Discount.objects.filter(user=request.user, used=True)

        
        total_discount_amount = Decimal('0.00')
        for discount in used_discounts:
            total_discount_amount += total_price * (discount.amount / Decimal(100))

        
        total_price_after_discount = total_price - total_discount_amount

        
        subject = 'Order Confirmation'
        html_message = render_to_string('confirmation_email.html', {
            'address': address,
            'first_name': first_name,
            'last_name': last_name,
            'city': city,
            'country': country,
            'zip_code': zip_code,
            'total_price': total_price_after_discount,  
            'basket_items': basket.items.all(),  
            'used_discounts': used_discounts,
        })
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL  
        to_email = [request.user.email]
        send_mail(subject, plain_message, from_email, to_email, html_message=html_message)

        
        basket.items.all().delete()

        
        used_discounts.delete()
        return redirect('index')  

    return render(request, 'checkout.html')

def update_meal_product(request, meal_product_id):
    meal_product = get_object_or_404(MealProduct, id=meal_product_id)
    if request.method == 'POST':
        new_quantity = Decimal(request.POST.get('quantity_grams'))
        old_quantity = meal_product.quantity_grams  
        meal_product.quantity_grams = new_quantity
        meal_product.save()

        
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
        old_quantity = meal_product.quantity_grams  
        meal_product.delete()

        
        meal = Meal.objects.get(pk=meal_id)
        meal.total_calories -= (meal_product.product.kcal_per_100g * old_quantity / 100)
        meal.total_proteins -= (meal_product.product.protein_per_100g * old_quantity / 100)
        meal.total_carbs -= (meal_product.product.carbs_per_100g * old_quantity / 100)
        meal.total_fats -= (meal_product.product.fats_per_100g * old_quantity / 100)

        
        meal.total_calories = max(meal.total_calories, 0)
        meal.total_proteins = max(meal.total_proteins, 0)
        meal.total_carbs = max(meal.total_carbs, 0)
        meal.total_fats = max(meal.total_fats, 0)

        meal.save()

        
        if meal.mealproduct_set.count() == 0 and meal.mealapiproduct_set.count() == 0:
            meal.delete()
            return redirect('calculator')

        return redirect('meal_detail', meal_id=meal_id)

    raise Http404("Invalid request method")

def update_meal_api_product(request, meal_api_product_id):
    meal_api_product = get_object_or_404(MealApiProduct, id=meal_api_product_id)
    if request.method == 'POST':
        new_quantity = Decimal(request.POST.get('quantity_grams'))
        old_quantity = meal_api_product.quantity_grams  
        meal_api_product.quantity_grams = new_quantity
        meal_api_product.save()

        
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
        old_quantity = meal_api_product.quantity_grams  
        meal_api_product.delete()

        
        meal = Meal.objects.get(pk=meal_id)
        meal.total_calories -= (meal_api_product.kcal_per_100g * old_quantity / 100)
        meal.total_proteins -= (meal_api_product.protein_per_100g * old_quantity / 100)
        meal.total_carbs -= (meal_api_product.carbs_per_100g * old_quantity / 100)
        meal.total_fats -= (meal_api_product.fats_per_100g * old_quantity / 100)

        
        meal.total_calories = max(meal.total_calories, 0)
        meal.total_proteins = max(meal.total_proteins, 0)
        meal.total_carbs = max(meal.total_carbs, 0)
        meal.total_fats = max(meal.total_fats, 0)

        meal.save()

        
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
        
        return redirect('create_profile')

    
    if user_profile.gender == 'male':
        bmr = 88.362 + (13.397 * float(user_profile.weight)) + (4.799 * float(user_profile.height)) - (5.677 * float(user_profile.age))
    else:  
        bmr = 447.593 + (9.247 * float(user_profile.weight)) + (3.098 * float(user_profile.height)) - (4.330 * float(user_profile.age))

    
    activity_levels = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    adjusted_bmr = bmr * activity_levels[user_profile.activity_level]

    
    if user_profile.goal == 'cut':
        daily_calories = adjusted_bmr - 500  
    elif user_profile.goal == 'bulk':
        daily_calories = adjusted_bmr + 500  
    else:  
        daily_calories = adjusted_bmr  

    user_profile.daily_calories = daily_calories
    user_profile.save()

    
    breakfast = Meal.objects.filter(meal_type='Breakfast', user=user).first()
    lunch = Meal.objects.filter(meal_type='Lunch', user=user).first()
    dinner = Meal.objects.filter(meal_type='Dinner', user=user).first()
    snacks = Meal.objects.filter(meal_type='Snacks', user=user).first()

    
    breakfast_products = MealProduct.objects.filter(meal__meal_type='Breakfast', meal__user=user)
    lunch_products = MealProduct.objects.filter(meal__meal_type='Lunch', meal__user=user)
    dinner_products = MealProduct.objects.filter(meal__meal_type='Dinner', meal__user=user)
    snacks_products = MealProduct.objects.filter(meal__meal_type='Snacks', meal__user=user)

    breakfast_api_products = MealApiProduct.objects.filter(meal__meal_type='Breakfast', meal__user=user)
    lunch_api_products = MealApiProduct.objects.filter(meal__meal_type='Lunch', meal__user=user)
    dinner_api_products = MealApiProduct.objects.filter(meal__meal_type='Dinner', meal__user=user)
    snacks_api_products = MealApiProduct.objects.filter(meal__meal_type='Snacks', meal__user=user)

    
    breakfast_total = calculate_total_nutritional_data(breakfast, breakfast_products, breakfast_api_products)
    lunch_total = calculate_total_nutritional_data(lunch, lunch_products, lunch_api_products)
    dinner_total = calculate_total_nutritional_data(dinner, dinner_products, dinner_api_products)
    snacks_total = calculate_total_nutritional_data(snacks, snacks_products, snacks_api_products)

    
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
        'breakfast_total_calories': breakfast_total['total_calories'],
        'lunch_total_calories': lunch_total['total_calories'],
        'dinner_total_calories': dinner_total['total_calories'],
        'snacks_total_calories': snacks_total['total_calories'],
    }
    return render(request, 'calculator.html', context)


@login_required
def create_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()
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
        
        search_results = search_product(search_query, user=user)
        for product in search_results:
                if isinstance(product, Product):
                    product.source = 'database'
                elif isinstance(product, ApiProduct):
                    product.source = 'api'
                else:
                    
                   pass
    if 'add_to_meal' in request.POST:
        product_id = request.POST.get('add_to_meal')
        quantity = request.POST.get(f'quantity_{product_id}')

        if product_id and quantity:
            try:
                product = Product.objects.get(pk=product_id)
                meal, created = Meal.objects.get_or_create(meal_type=meal_type, user=user)
                meal_product = meal.add_product(product, quantity)  
                return redirect('add_to_meal', meal_type=meal_type)
            except Product.DoesNotExist:
                try:
                    api_product = ApiProduct.objects.get(pk=product_id)
                    meal, created = Meal.objects.get_or_create(meal_type=meal_type, user=user)
                    meal_api_product = meal.add_product(api_product, quantity)  
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
        form = UserProfileForm(request.POST, instance=user.userprofile)  
        if form.is_valid():
            form.save()
            return redirect('myprofile')  
    else:
        form = UserProfileForm(instance=user.userprofile)  

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

    
    if request.user == comment.user or (comment.post.user and request.user == comment.post.user):
        
        comment.delete()

    
    return redirect('post', post_id=comment.post.id)


@login_required
def create_post(request):
    
    try:
        banned = Banned.objects.get(user=request.user)
        if banned.banned_until and banned.banned_until > timezone.now():
            
            banned_until = banned.banned_until.strftime("%Y-%m-%d %H:%M:%S")
            return redirect('banned_info')  
        else:
            
            banned.delete()
    except Banned.DoesNotExist:
        pass  
    
    
    products = Product.objects.all().order_by('product_name')
    api_products = ApiProduct.objects.all().order_by('product_name')

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            product_type = form.cleaned_data.get('product_type')
            content = form.cleaned_data.get('content')
            title = form.cleaned_data.get('title')

            
            user = request.user

            post = Post(content=content, title=title, user=user, product_type=product_type)

            
            if product_type == 'Product':
                product_instance_id = form.cleaned_data.get('object_id')
                try:
                    product_instance = Product.objects.get(id=product_instance_id)
                    post.product = product_instance
                    post.product_name = product_instance.product_name  
                except Product.DoesNotExist:
                    return render(request, 'create_post.html', {'form': form, 'products': products, 'api_products': api_products, 'error_message': 'Selected product does not exist'})
            elif product_type == 'ApiProduct':
                api_product_instance_id = form.cleaned_data.get('object_id')
                try:
                    api_product_instance = ApiProduct.objects.get(id=api_product_instance_id)
                    post.product = api_product_instance
                    post.product_name = api_product_instance.product_name  
                except ApiProduct.DoesNotExist:
                    return render(request, 'create_post.html', {'form': form, 'products': products, 'api_products': api_products, 'error_message': 'Selected API product does not exist'})

            post.save()

            return redirect('index')
    else:
        
        initial_product_type = request.GET.get('product_type', 'Product')  
        form = PostForm(initial={'product_type': initial_product_type})
        form.set_product_choices(initial_product_type)  

    return render(request, 'create_post.html', {'form': form, 'products': products, 'api_products': api_products})

@login_required
def post_list(request):
    posts = Post.objects.order_by('-pub_date')  
    return render(request, 'post_list.html', {'posts': posts})

def post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = Comment.objects.filter(post=post).order_by('-pub_date')

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()
            
            return redirect('post', post_id=post_id)
    else:
        comment_form = CommentForm()

    return render(request, 'post.html', {'post': post, 'comment_form': comment_form, 'comments': comments})


def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)

    
    if request.user != comment.user:
        
        return redirect('some_other_page')  

    if request.method == 'POST':
        
        comment.content = request.POST.get('content')
        comment.save()
        
        return redirect('post', post_id=comment.post.id)

    
    

    return redirect('post', post_id=comment.post.id)  


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    products = Product.objects.all().order_by('product_name')
    api_products = ApiProduct.objects.all().order_by('product_name')


    
    if request.user != post.user:
        return redirect('post', post_id=post_id)

    if request.method == 'POST':
        
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            
            updated_post = form.save(commit=False)

            
            updated_post.user = request.user

            
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

            
            updated_post.save()
            return redirect('my_posts')
    else:
        
        form = PostForm(instance=post)
    
    return render(request, 'edit_post.html', {'form': form, 'products': products, 'api_products': api_products})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    
    if request.user != post.user:
        messages.error(request, "You do not have permission to delete this post.")
        return redirect('post', post_id=post_id)

    if request.method == 'POST':
        
        post.delete()
        return redirect('my_posts')
    else:
        
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
        except Post.DoesNotExist:
            messages.error(request, 'Post does not exist.')
    return redirect('post_list')

@login_required
def manage_ban(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST' and request.user.is_superuser:
        try:
            ban_duration_minutes = int(request.POST.get('ban_duration', 2))  
            ban_end_date = timezone.now() + timedelta(minutes=ban_duration_minutes)
            banned, created = Banned.objects.get_or_create(user=user)
            banned.banned_until = ban_end_date
            banned.save()
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


def add_to_recipe(request, recipe_id):
    search_query = request.POST.get('product_name', '')
    search_results = []

    if search_query.strip():
        
        search_results = search_product(search_query)
        for product in search_results:
            if isinstance(product, Product):
                product.source = 'database'
            elif isinstance(product, ApiProduct):
                product.source = 'api'
            else:
                
                pass

    if 'add_to_recipe' in request.POST:
        product_id = request.POST.get('add_to_recipe')
        quantity = request.POST.get(f'quantity_{product_id}')

        if product_id and quantity:
            try:
                product = Product.objects.get(pk=product_id)
                source = 'database'
            except Product.DoesNotExist:
                try:
                    product = ApiProduct.objects.get(pk=product_id)
                    source = 'api'
                except ApiProduct.DoesNotExist:
                    messages.error(request, "Product not found.")
                    return redirect('all_recipes')

            recipe = get_object_or_404(Recipe, pk=recipe_id)
            try:
                if source == 'database':
                    ingredient = Ingredient.objects.get(recipe=recipe, source=source, product=product)
                elif source == 'api':
                    
                    ingredient = Ingredient.objects.create(recipe=recipe, source=source, api_product=product, quantity=int(quantity))
            except Ingredient.DoesNotExist:
                
                if source == 'database':
                    ingredient = Ingredient.objects.create(recipe=recipe, source=source, product=product, quantity=int(quantity))
                elif source == 'api':
                    messages.error(request, "API Product not found.")
                    return redirect('all_recipes')

            
            if source == 'database':
                ingredient.quantity += int(quantity)
                ingredient.save()

            return redirect('all_recipes')
        else:
            messages.error(request, "Please provide both a product and a quantity.")

    context = {'recipe_id': recipe_id, 'search_results': search_results, 'search_query': search_query}
    return render(request, 'add_to_recipe.html', context)

@login_required
def all_recipes(request):
    recipes = Recipe.objects.all()
    context = {'recipes': recipes}
    return render(request, 'all_recipes.html', context)


@login_required
def manage_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    form = RecipeForm(instance=recipe)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_quantity':
            ingredient_id = request.POST.get('ingredient_id')
            new_quantity = request.POST.get('quantity')
            ingredient = get_object_or_404(Ingredient, id=ingredient_id)
            ingredient.quantity = new_quantity
            ingredient.save()
        elif action == 'delete':
            ingredient_id = request.POST.get('ingredient_id')
            ingredient = get_object_or_404(Ingredient, id=ingredient_id)
            ingredient.delete()
        else:
            form = RecipeForm(request.POST, instance=recipe)
            if form.is_valid():
                form.save()

    context = {'recipe': recipe, 'form': form}
    return render(request, 'manage_recipe.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)  
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.image = form.cleaned_data['image']  
            recipe.save()
            return redirect('all_recipes')
    else:
        form = RecipeForm()

    context = {'form': form}
    return render(request, 'create_recipe.html', context)