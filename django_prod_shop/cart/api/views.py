from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from typing import Any

from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework import status

from django.db import transaction
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, QuerySet

from django_prod_shop.products.models import Product
from django_prod_shop.cart.api.serializers import (CartSerializer, CartAddSerializer, 
                                                   CartUpdateSerializer, ApplyCouponSerializer)
from django_prod_shop.cart.models import Cart, CartItem
from django_prod_shop.cart.services import get_or_create_cart, get_cart_cache_key


class CartViewSet(GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_cart_queryset(self) -> QuerySet[Cart]:
        return Cart.objects.select_related('user').select_related('coupon').prefetch_related(
            Prefetch('cart_items', queryset=CartItem.objects.select_related('product'))
        )

    def get_cart(self) -> Cart:
        cart = get_or_create_cart(self.request)
        return self.get_cart_queryset().get(pk=cart.pk)

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        cache_key = get_cart_cache_key(request)
        cached_cart = cache.get(cache_key)

        if cached_cart is not None:
            return Response(cached_cart, status=status.HTTP_200_OK)

        cart = self.get_cart()
        data = self.get_serializer(cart).data
        cache.set(cache_key, data, 60*60)

        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['cart'],
        summary='Добавить товар в корзину',
        description=(
            'Добавляет активный товар в корзину по его slug. '
            'Если товар уже есть в корзине, увеличивает его количество. '
            'Количество должно быть не меньше 1. '
            'Если товара недостаточно на складе или товар не найден, возвращает ошибку 400.'
        ),
        request=CartAddSerializer,
        responses={
            status.HTTP_200_OK: CartSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                name='Добавление товара в корзину',
                value={
                    'product_slug': 'iphone-22-pro',
                    'quantity': 2,
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Товар не найден',
                value={
                    'product_slug': ['Такого товара не существует'],
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Недостаточно товара',
                value={
                    'quantity': ['Недостаточно товара на складе'],
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Недостаточно товара при добавлении к существующей позиции',
                value={
                    'quantity': 'Недостаточно товара на складе. Доступно: 3',
                },
                response_only=True,
                status_codes=['400'],
            ),
        ],
    )
    @action(detail=False, methods=['post'], url_path='items', url_name='add-to-cart')
    def add_to_cart(self, request: Request) -> Response:
        cart = self.get_cart()
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.context['product']
        quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            locked_product = Product.objects.select_for_update().get(pk=product.pk)
            available_quantity = locked_product.quantity - locked_product.reserved_quantity

            if quantity > available_quantity:
                return Response(
                    {'quantity': f'Недостаточно товара на складе. Доступно: {available_quantity}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item = CartItem.objects.select_for_update().filter(cart=cart, product=locked_product).first()

            if item is None:
                CartItem.objects.create(cart=cart, product=locked_product, quantity=quantity)
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
    
    @extend_schema(
        tags=['cart'],
        summary='Обновить количество товара в корзине',
        description=(
            'Обновляет количество товара в корзине по его item_id. '
            'Если quantity = 0, позиция удаляется из корзины. '
            'Если указанное количество больше доступного остатка товара, возвращает ошибку 400.'
        ),
        parameters=[
            OpenApiParameter(
                name='item_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='ID товара в корзине',
                required=True,
            ),
        ],
        request=CartUpdateSerializer,
        responses={
            status.HTTP_200_OK: CartSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                name='Обновление количества',
                value={
                    'quantity': 3,
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Удаление товара через quantity = 0',
                value={
                    'quantity': 0,
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Недостаточно товара',
                value={
                    'quantity': 'Недостаточно товара на складе. Доступно: 2',
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Товар в корзине не найден',
                value={
                    'detail': 'Not found.',
                },
                response_only=True,
                status_codes=['404'],
            ),
        ],
    )
    @action(detail=False, methods=['patch'], url_path=r'items/(?P<item_id>\d+)/update', url_name='update-cart-item')
    def update_cart_item(self, request: Request, item_id: int | None = None) -> Response:
        cart = self.get_cart()
        item = get_object_or_404(CartItem, cart=cart, id=item_id)

        serializer = CartUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            item = CartItem.objects.select_for_update().get(id=item.pk)
            locked_product = Product.objects.select_for_update().get(pk=item.product_id)

            if quantity == 0:
                item.delete()
            else:
                available_quantity = locked_product.quantity - locked_product.reserved_quantity
                if quantity > available_quantity:
                    return Response(
                        {'quantity': f'Недостаточно товара на складе. Доступно: {available_quantity}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                item.quantity = quantity
                item.save(update_fields=['quantity'])

        cart = self.get_cart()
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['cart'],
        summary='Удалить товар из корзины',
        description=(
            'Удаляет товар из корзины по его item_id. '
            'Если товар в корзине не найден, возвращает ошибку 404.'
        ),
        parameters=[
            OpenApiParameter(
                name='item_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='ID товара в корзине',
                required=True,
            ),
        ],
        request=None,
        responses={
            status.HTTP_200_OK: CartSerializer,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                name='Товар в корзине не найден',
                value={
                    'detail': 'Not found.',
                },
                response_only=True,
                status_codes=['404'],
            ),
        ],
    )
    @action(detail=False, methods=['delete'], url_path=r'items/(?P<item_id>\d+)/remove', url_name='remove-cart-item')
    def remove_cart_item(self, request: Request, item_id: int | None = None) -> Response:
        cart = self.get_cart()
        item = get_object_or_404(CartItem, cart=cart, id=item_id)
        item.delete()

        cart = self.get_cart()
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)
    
    @extend_schema(
        tags=['cart'],
        summary='Очистить корзину',
        description=(
            'Очищает корзину.'
        ),
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description='Корзина успешно очищена. Тело ответа отсутствует.'
            ),
        },
    )
    @action(detail=False, methods=['delete'], url_path='clear', url_name='clear-cart')
    def clear_cart(self, request: Request) -> Response:
        cart = self.get_cart()
        cart.cart_items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        tags=['cart'],
        summary='Применить купон к корзине',
        description=(
            'Применяет активный купон к корзине. '
            'Если купон неактивен или не существует, возвращает ошибку 400.'
        ),
        request=ApplyCouponSerializer,
        responses={
            status.HTTP_200_OK: CartSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                name='Применение купона',
                value={
                    'code': 'ultra-test-coupon',
                },
                request_only=True,
            ),
            OpenApiExample(
                name='Купона не существует',
                value={
                    'code': ['Такого купона не существует'],
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Купон неактивен',
                value={
                    'code': ['Данный купон неактивен'],
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Срок действия купона ещё не начался',
                value={
                    'code': ['Срок действия купона ещё не начался'],
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Срок действия купона истёк',
                value={
                    'code': ['Срок действия купона истёк'],
                },
                response_only=True,
                status_codes=['400'],
            ),
        ],
    )
    @action(detail=False, methods=['post'], url_path='apply-coupon', url_name='apply-coupon')
    def apply_coupon(self, request: Request) -> Response:
        cart = self.get_cart()

        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        coupon = serializer.context['coupon']
        cart.coupon = coupon
        cart.save(update_fields=['coupon', 'updated_at'])

        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['cart'],
        summary='Удалить примененный купон',
        description='Удаляет примененный к корзине купон.',
        request=None,
        responses={
            status.HTTP_200_OK: CartSerializer,
        },
    )
    @action(detail=False, methods=['delete'], url_path='remove-coupon', url_name='remove-coupon')
    def remove_coupon(self, request: Request) -> Response:
        cart = self.get_cart()
        cart.coupon = None
        cart.save(update_fields=['coupon', 'updated_at'])

        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK) 
