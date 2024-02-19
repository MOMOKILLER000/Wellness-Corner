from django.urls import path
from . import views
from .views import registration_view, login_view
urlpatterns = [
    path('', views.index, name='index'),
    path('rate/<int:product_id>/<str:source>/', views.rate_product, name='rate_product'),
    path('register/', registration_view, name='register'),
    path('login/', login_view, name='login'),
    path('product/<int:product_id>/<str:source>/', views.product_detail, name='product_detail'),
]
