from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import filters

from django_filters import rest_framework as dj_filters

from django_prod_shop.products.models import Category, Product
from django_prod_shop.products.pagination import CustomPaginator
from django_prod_shop.products.filters import ProductFilter
from .serializers import CategorySerializer, ProductSerializer


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('category')
    pagination_class = CustomPaginator
    filter_backends = [dj_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['title', 'category__title']
    ordering_fields = ['title', 'price', 'created_at']
    ordering = ['-created_at']
    lookup_field = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            return qs.filter(is_active=True)
        
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        
        return [permission() for permission in permission_classes]



class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.prefetch_related('products')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title']
    orderng_fileds = ['title']
    ordering = ['title']
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        
        return [permission() for permission in permission_classes]
