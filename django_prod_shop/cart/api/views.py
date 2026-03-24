from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from django_prod_shop.cart.api.serializers import CartSerializer, CartAddSerializer, CartUpdateSerializer
from django_prod_shop.cart.models import Cart, CartItem
from django_prod_shop.coupons.models import Coupon
from django_prod_shop.cart.services import get_or_create_cart, get_cart_cache_key


class CartViewSet(ListModelMixin, GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_cart_queryset(self):
        return Cart.objects.select_related('user').select_related('coupon').prefetch_related(
            Prefetch('cart_items', queryset=CartItem.objects.select_related('product'))
        )

    def get_cart(self):
        cart = get_or_create_cart(self.request)
        return self.get_cart_queryset().get(pk=cart.pk)

    def list(self, request, *args, **kwargs):
        cache_key = get_cart_cache_key(request)
        cached_cart = cache.get(cache_key)

        if cached_cart is not None:
            return Response(cached_cart, status=status.HTTP_200_OK)

        cart = self.get_cart()
        data = self.get_serializer(cart).data
        cache.set(cache_key, data, 60*60)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='items', url_name='add-to-cart')
    def add_to_cart(self, request):
        cart = self.get_cart()
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.context['product']
        quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            available_quantity = product.quantity - product.reserved_quantity

            if quantity > available_quantity:
                return Response(
                    {'quantity': f'Недостаточно товара на складе. Доступно: {available_quantity}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item = CartItem.objects.select_for_update().filter(cart=cart, product=product).first()

            if item is None:
                CartItem.objects.create(cart=cart, product=product, quantity=quantity)
            else:
                new_quantity = item.quantity + quantity
                
                if new_quantity > available_quantity:
                    return Response(
                        {'quantity': f'Недостаточно товара на складе. Доступно: {available_quantity}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                
                item.quantity = new_quantity
                item.save(update_fields=['quantity'])

        cart = self.get_cart()
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['patch'], url_path=r'items/(?P<item_id>\d+)/update', url_name='update-cart-item')
    def update_cart_item(self, request, item_id=None):
        cart = self.get_cart()
        item = get_object_or_404(CartItem, cart=cart, id=item_id)

        serializer = CartUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            item = CartItem.objects.select_related('product').select_for_update().get(id=item.pk)
            if quantity == 0:
                item.delete()
            else:
                available_quantity = item.product.quantity - item.product.reserved_quantity
                if quantity > available_quantity:
                    return Response(
                        {'quantity': f'Недостаточно товара на складе. Доступно: {available_quantity}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                item.quantity = quantity
                item.save(update_fields=['quantity'])

        cart = self.get_cart()
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path=r'items/(?P<item_id>\d+)/remove', url_name='remove-cart-item')
    def remove_cart_item(self, request, item_id=None):
        cart = self.get_cart()
        item = get_object_or_404(CartItem, cart=cart, id=item_id)
        item.delete()

        cart = self.get_cart()
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='clear', url_name='clear-cart')
    def clear_cart(self, request):
        cart = self.get_cart()
        cart.cart_items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path=r'apply-coupon/(?P<code>[^/.]+)', url_name='apply-coupon')
    def apply_coupon(self, request, code=None):
        cart = self.get_cart()
        coupon = get_object_or_404(Coupon, code=code)
        if not coupon.is_active:
            return Response({'code': 'Данный купон неактивен'}, status=status.HTTP_400_BAD_REQUEST)
        cart.coupon = coupon
        cart.save()
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)
