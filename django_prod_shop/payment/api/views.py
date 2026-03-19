from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.urls import reverse

from django_prod_shop.orders.models import Order
from django_prod_shop.payment.services import create_payment
from .serializers import PaymentSerializer


class PaymentViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        if self.request.user.is_staff:
            return qs
        
        return qs.filter(order__user=self.request.user)

    def get_permissions(self):
        if self.action in ['retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        
        return [permission() for permission in permission_classes]

    def create(self, request, order_id):
        return create_payment(request, order_id)


@api_view(['GET'])
def payment_completed(request):
    return Response({'payment_status': 'completed', 'redirect_url': reverse('orders:orders-list')})
