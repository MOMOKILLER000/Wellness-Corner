from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth import authenticate, login, logout
from .models import Product, ApiProduct, Allergy, Basket, BasketItem
from .forms import RegistrationForm, LoginForm
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
from .forms import PostForm, EmailSubscriberForm, ContactForm, NewsletterSubscriptionForm
from .models import Post
from django.db.models import F
from itertools import chain
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied

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
                
            return HttpResponseRedirect(reverse('product_created'))  # Redirect to the success page
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
def create_post(request):
    products = Product.objects.all()
    api_products = ApiProduct.objects.all()

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

def post_list(request):
    posts = Post.objects.all()
    return render(request, 'post_list.html', {'posts': posts})

def post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    return render(request, 'post.html', {'post': post})


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
            form.save_subscription(request.user)
            messages.success(request, 'Subscription successful.')
            return redirect('index')
    else:
        form = NewsletterSubscriptionForm()

    return render(request, 'index.html', {'form': form})