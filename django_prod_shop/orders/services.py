from decimal import Decimal

from django.db.models import Prefetch
from django.db import transaction

from rest_framework.serializers import ValidationError

from django_prod_shop.cart.models import Cart, CartItem
from .models import Order, OrderItem


@transaction.atomic
def create_order(user, validated_data):
    cart = Cart.objects.select_related('user').select_related('coupon').prefetch_related(
        Prefetch('cart_items', queryset=CartItem.objects.select_related('product'))
    ).filter(user=user).first()

    if cart is None:
        raise ValidationError('У пользователя нет корзины')
    cart_items = list(cart.cart_items.all())
    if not cart_items:
        raise ValidationError('Корзина пуста')
    
    if cart.coupon_id:
        validated_data['coupon'] = cart.coupon

    order = Order.objects.create(user=user, **validated_data)
    total_before_discount = Decimal('0.00')
    order_items = []

    for item in cart_items:
        price = item.product.price
        quantity = item.quantity

        order_items.append(OrderItem(
            order=order, product=item.product, 
            quantity=quantity, price=price,
        ))
        total_before_discount += price * quantity

    OrderItem.objects.bulk_create(order_items)

    discount = total_before_discount * (Decimal(order.discount) / Decimal('100'))
    order.total_price = total_before_discount - discount
    order.save(update_fields=['total_price'])
    
    cart.cart_items.all().delete()
    cart.delete()

    return order
