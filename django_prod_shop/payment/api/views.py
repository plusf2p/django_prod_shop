from django.urls import reverse

from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response

from django_prod_shop.payment.permissions import CanChangePayment
from django_prod_shop.payment.models import Payment
from django_prod_shop.payment.services import create_payment_service
from .serializers import PaymentSerializer


class PaymentViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Payment.objects.select_related('order', 'order__user')
    serializer_class = PaymentSerializer
    lookup_field = 'payment_id'

    def get_queryset(self):
        qs = super().get_queryset()

        if self.request.user.has_perm('payment.manage_payments'):
            return qs
        
        return qs.filter(order__user=self.request.user)

    def get_permissions(self):
        if self.action in ['create_payment', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [CanChangePayment]
        
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path=r'create/(?P<order_id>[^/.]+)', url_name='create')
    def create_payment(self, request, order_id=None):
        return create_payment_service(request, order_id)


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def payment_completed(request):
    return Response({
        'payment_status': 'completed', 
        'redirect_url': request.build_absolute_uri(reverse('orders:orders-list')),
    })
