from django.urls import path

from rest_framework.routers import DefaultRouter

from .api import views as api_views
from . import views


app_name = 'products'

router = DefaultRouter()
router.register('products', api_views.ProductViewSet)
router.register('category', api_views.CategoryViewSet)

urlpatterns = [
    path('', views.index, name='index'),
]

urlpatterns += router.urls
