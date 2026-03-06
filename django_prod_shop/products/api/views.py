from rest_framework.viewsets import ModelViewSet

from django_prod_shop.products.models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.prefetch_related('products')


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('category')
