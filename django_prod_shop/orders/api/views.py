from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from django_prod_shop.orders.permissions import CanChangeOrders
from django_prod_shop.orders.models import Order, OrderItem
from .serializers import OrderReadSerializer, OrderWriteSerializer


@api_view(['POST'])
@permission_classes([CanChangeOrders])
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

        qs = Order.objects.select_related('user').select_related('coupon').prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        )
        if user.has_perm('orders.manage_orders'):
            return qs
        
        return qs.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderWriteSerializer
        return OrderReadSerializer

    def retrieve(self, request, order_id, *args, **kwargs):
        cache_key = f'order_retrieve_{order_id}'
        cached_order = cache.get(cache_key)

        if cached_order is not None:
            return Response(cached_order)
        
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60*60)

        return Response(response.data, status=status.HTTP_200_OK)
