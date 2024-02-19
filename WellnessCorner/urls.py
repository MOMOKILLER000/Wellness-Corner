from django.urls import path
from . import views
from .views import registration_view, login_view, add_allergy
urlpatterns = [
    path('', views.index, name='index'),
    path('rate/<int:product_id>/<str:source>/', views.rate_product, name='rate_product'),
    path('register/', registration_view, name='register'),
    path('login/', login_view, name='login'),
    path('add_allergy/', add_allergy, name='add_allergy'),
]
