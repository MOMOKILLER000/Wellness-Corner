from django.urls import path
from . import views
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
    path('approve-products/', views.approve_products, name='approve_products'),
    path('pending-products/', views.pending_products, name='pending_products'),
]
