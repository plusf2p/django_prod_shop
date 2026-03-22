from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.filters import OrderingFilter

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from django_prod_shop.reviews.models import Review
from django_prod_shop.reviews.permissions import IsManagerOrAdminOrOrAuthor, IsManagerOrAdmin
from .serializers import ReviewSerializer


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related('product').select_related('user')
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsManagerOrAdminOrOrAuthor]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action == 'retrieve':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsManagerOrAdmin]

        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        return serializer.save(user=self.request.user)
    
    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
    
    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='review_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='review_retrieve'))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
