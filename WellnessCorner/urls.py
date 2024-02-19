from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('rate/<int:product_id>/<str:source>/', views.rate_product, name='rate_product'),
]
