from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.filters import OrderingFilter

from django_prod_shop.reviews.models import Review
from django_prod_shop.reviews.permissions import IsAdminOrAuthor
from .serializers import ReviewSerializer


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related('product').select_related('user')
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    lookup_field = 'id'

    def get_queryset(self):
        qs = super().get_queryset()

        if self.action in ['update', 'partial_update', 'destroy']:
            qs = qs.filter(user=self.request.user)

        return qs

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAdminOrAuthor]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action == 'retrieve':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        return serializer.save(user=self.request.user)
    
    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
