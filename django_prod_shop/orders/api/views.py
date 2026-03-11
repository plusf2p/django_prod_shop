from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from django_prod_shop.orders.models import Order, OrderItem
from .serializers import OrderReadSerializer, OrderWriteSerializer


@api_view(['POST'])
@permission_classes([IsAdminUser])
def change_order_status_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    order_status = request.data.get('status')
    allowed_status = [choice[0] for choice in Order.StatusChoices.choices]
    if order_status not in allowed_status:
        return Response({'error': 'Такого статуса не существует'}, status=status.HTTP_400_BAD_REQUEST)

    order.status = order_status
    order.save(update_fields=['status'])

    serializer = OrderReadSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)


class OrderViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'

    def get_queryset(self):
        user = self.request.user

        qs = Order.objects.select_related('user').prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        )
        if user.is_staff:
            return qs
        
        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderWriteSerializer
        return OrderReadSerializer
