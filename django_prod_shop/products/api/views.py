from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from rest_framework import filters

from django_filters import rest_framework as dj_filters

from django.db.models import Prefetch, Avg, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from django_prod_shop.reviews.models import Review
from django_prod_shop.products.models import Category, Product
from django_prod_shop.products.pagination import CustomPaginator
from django_prod_shop.products.filters import ProductFilter
from django_prod_shop.products.permissions import CanChangeProducts, CanChangeCategories
from .serializers import (CategoryDetailSerializer, CategoryListSerializer, CategoryWriteSerializer,
                          ProductReadSerializer, ProductDetailSerializer, ProductWriteSerializer)


class ProductViewSet(ModelViewSet):
    serializer_class = ProductReadSerializer
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

        if self.action == 'list':
            qs = qs.annotate(rating=Avg('reviews__rating'), reviews_count=Count('reviews'))
        elif self.action == 'retrieve':
            qs = qs.prefetch_related(
                Prefetch('reviews', queryset=Review.objects.select_related('user'))
            ).annotate(rating=Avg('reviews__rating'), reviews_count=Count('reviews'))
        
        if not self.request.user.has_perm('products.manage_products'):
            return qs.filter(is_active=True)
        
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [CanChangeProducts]
        else:
            permission_classes = [AllowAny]
        
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return ProductWriteSerializer
        return ProductReadSerializer

    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='product_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='product_retrieve'))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class CategoryViewSet(ModelViewSet):
    serializer_class = CategoryListSerializer
    queryset = Category.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title']
    ordering_fields = ['title']
    ordering = ['title']
    lookup_field = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action == 'retrieve':
            qs = qs.prefetch_related(
                Prefetch('products', queryset=Product.objects.select_related('category').annotate(
                    rating=Avg('reviews__rating'), reviews_count=Count('reviews')
            )))
        
        if not self.request.user.has_perm('products.manage_categories'):
            return qs.filter(is_active=True)
        
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [CanChangeCategories]
        else:
            permission_classes = [AllowAny]
        
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list':
            return CategoryListSerializer
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return CategoryWriteSerializer
        return CategoryDetailSerializer

    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='category_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='category_retrieve'))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
