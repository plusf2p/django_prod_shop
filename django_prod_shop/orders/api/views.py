from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.db import transaction

from django_prod_shop.orders.models import Order, OrderItem
from .serializers import OrderReadSerializer, OrderWriteSerializer


@api_view(['POST'])
@csrf_exempt
@permission_classes([IsAdminUser])
def change_status_view(request, order_id, order_status):
    try:
        order = get_object_or_404(Order, order_id=order_id)
        order.status = order_status
        order.save()
        serializer = OrderWriteSerializer(order)
        serializer.save(user=request.user)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.data, status=status.HTTP_200_OK)


class OrderViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    queryset = Order.objects.select_related('user').prefetch_related(
        Prefetch('items', queryset=OrderItem.objects.select_related('product'))
    )
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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
