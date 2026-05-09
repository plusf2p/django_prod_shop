from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from rest_framework.serializers import ValidationError

from django_prod_shop.products.models import Product
from django_prod_shop.cart.models import Cart
from .models import Order, OrderItem


@transaction.atomic
def create_order(user: AbstractBaseUser, validated_data: dict[str, Any]) -> Order:
    cart = Cart.objects.select_for_update().select_related('user').prefetch_related(
        'cart_items'
    ).filter(user=user).first()

    if cart is None:
        raise ValidationError({'error': 'У пользователя нет корзины'})
    
    cart_items = list(cart.cart_items.all())
    if not cart_items:
        raise ValidationError({'error': 'Корзина пуста'})
    
    locked_products: dict[int, Product] = {}

    for cart_item in cart_items:
        product = Product.objects.select_for_update().get(pk=cart_item.product_id)
        locked_products[cart_item.product_id] = product

        if not product.is_active:
            raise ValidationError({'error': f'Товар "{product.title}" недоступен для заказа'})
        
        available_quantity = product.quantity - product.reserved_quantity
        if cart_item.quantity > available_quantity:
            raise ValidationError({'error': f'Недостаточно товара "{product.title}" на складе'})
    
    if cart.coupon_id:
        validated_data['coupon'] = cart.coupon

    order = Order.objects.create(user=user, **validated_data)
    total_before_discount = Decimal('0.00')
    order_items: list[OrderItem] = []

    for item in cart_items:
        product = locked_products[item.product_id]
        price = product.price
        quantity = item.quantity

        order_items.append(OrderItem(
            order=order, product=product, 
            quantity=quantity, price=price,
        ))
        total_before_discount += price * quantity

    OrderItem.objects.bulk_create(order_items)

    if order.coupon_id:
        discount = total_before_discount * (Decimal(str(order.coupon.discount)) / Decimal('100'))
    else:
        discount = Decimal('0.00')
    order.total_price = total_before_discount - discount
    order.save(update_fields=['total_price'])

    cart.cart_items.all().delete()
    cart.delete()

    return order
