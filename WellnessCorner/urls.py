from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    path('rate/<int:product_id>/<str:source>/', views.rate_product, name='rate_product'),
    path('register/', views.registration_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('product/<int:product_id>/<str:source>/', views.product_detail, name='product_detail'),
    path('add_to_basket/<int:product_id>/<str:source>/', views.add_to_basket, name='add_to_basket'),
    path('basket/', views.basket_page, name='basket_page'),
    path('delete_from_basket/<int:product_id>/<str:source>/', views.delete_from_basket, name='delete_from_basket'),
    path('create/', views.create, name='create'),
    path('product_created/', views.product_created, name='product_created'),  # New URL for product creation success
    path('approve-products/', views.approve_products, name='approve_products'),
    path('pending-products/', views.pending_products, name='pending_products'),
    path('my-products/', views.my_products, name='my_products'),
    path('my-products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('my-products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('create-post/', views.create_post, name='create_post'),
    path('posts/', views.post_list, name='post_list'),
    path('post/<int:post_id>/', views.post, name='post'),
    path('contact/', views.contact, name='contact'),
    path('newsletter/', views.newsletter_subscription, name='newsletter_subscription'),
    path('send_email/', views.send_email_to_subscribers, name='send_email_to_subscribers'),
    path('increment_quantity/<int:product_id>/<str:source>/', views.increment_quantity, name='increment_quantity'),
    path('decrement_quantity/<int:product_id>/<str:source>/', views.decrement_quantity, name='decrement_quantity'),
    path('checkout/', views.checkout, name='checkout'),
    path('meal-detail/<int:meal_id>/', views.meal_detail, name='meal_detail'),
    path('calculator/', views.calculator, name='calculator'),  # Add this line
    path('add_to_meal/<str:meal_type>/', views.add_to_meal, name='add_to_meal'),
    path('update-meal-product/<int:meal_product_id>/', views.update_meal_product, name='update_meal_product'),
    path('delete-meal-product/<int:meal_product_id>/', views.delete_meal_product, name='delete_meal_product'),
    path('update-meal-api-product/<int:meal_api_product_id>/', views.update_meal_api_product, name='update_meal_api_product'),
    path('delete-meal-api-product/<int:meal_api_product_id>/', views.delete_meal_api_product, name='delete_meal_api_product'),
    path('create-profile/', views.create_profile, name='create_profile'),
    path('myaccount/', views.myaccount, name='myaccount'),
    path('password_change/', views.CustomPasswordChangeView.as_view(
        template_name='myaccount.html',
        success_url='/myaccount/'
    ), name='password_change'),
    path('myprofile/', views.myprofile, name='myprofile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

