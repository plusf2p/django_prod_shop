from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny

from django_prod_shop.products.models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.prefetch_related('products')
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('category')
    permission_classes = [AllowAny]
    lookup_field = 'slug'
