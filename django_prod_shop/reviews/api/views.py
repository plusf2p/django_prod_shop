from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.filters import OrderingFilter

from django_prod_shop.reviews.models import Review
from django_prod_shop.reviews.permissions import IsAdminOrAuthor, IsAdminOrBuyer
from .serializers import ReviewSerializer


class ReviewViewSet(ListModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related('product').select_related('user')
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action in ['update', 'partial_update', 'destroy']:
            qs = qs.filter(user=self.request.user)

        return qs

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminOrAuthor]
        elif self.action == 'create':
            permission_classes = [IsAdminOrBuyer]
        else:
            permission_classes = [AllowAny]

        return [permission() for permission in permission_classes]
