from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Prefetch

from django_prod_shop.orders.models import Order, OrderItem
from .serializers import OrderSerializer, OrderUpdateSerializer


class OrderViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.select_related('user').prefetch_related(
        Prefetch('items', queryset=OrderItem.objects.select_related('product'))
    )
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user

        qs = Order.objects.select_related('user').prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        )
        if user.is_staff:
            return qs
        
        return qs.filter(user=user)
