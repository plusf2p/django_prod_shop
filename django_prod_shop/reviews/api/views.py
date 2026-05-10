from typing import Any

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.request import Request

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from django_prod_shop.reviews.models import Review
from django_prod_shop.reviews.permissions import IsManagerOrAdminOrAuthor, IsManagerOrAdmin
from .serializers import ReviewSerializer


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related('product').select_related('user')
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    lookup_field = 'id'

    def get_permissions(self) -> list[BasePermission]:
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsManagerOrAdminOrAuthor]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action == 'retrieve':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsManagerOrAdmin]

        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer: ReviewSerializer) -> None:
        serializer.save(user=self.request.user)
    
    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='review_list'))
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().list(request, *args, **kwargs)
    
    @method_decorator(vary_on_headers('Authorization'))
    @method_decorator(cache_page(60*60, key_prefix='review_retrieve'))
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().retrieve(request, *args, **kwargs)
