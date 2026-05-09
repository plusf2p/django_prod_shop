from rest_framework.request import Request

from django.db import transaction
from django.contrib.auth.models import AbstractBaseUser

from .models import Cart, CartItem



def get_or_create_session_key(request: Request) -> str | None:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request: Request) -> Cart:
    user = request.user
    
    if user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    session_key = get_or_create_session_key(request)
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def get_cart_cache_key(request: Request) -> str:
    if request.user.is_authenticated:
        return f'cart_list_user_{request.user.pk}'
    session_key = get_or_create_session_key(request)
    return f'cart_list_session_{session_key}'


@transaction.atomic
def merge_cart(request: Request, user: AbstractBaseUser | None) -> None:
    if not user or not user.is_authenticated:
        return

    session_key = request.session.session_key
    if not session_key:
        return

    try:
        anon_cart = Cart.objects.select_for_update().get(session_key=session_key, user=None)
    except Cart.DoesNotExist:
        return
    
    try:
        user_cart = Cart.objects.select_for_update().get(user=user)
    except Cart.DoesNotExist:
        anon_cart.user = user
        anon_cart.session_key = None
        anon_cart.coupon = None
        anon_cart.save(update_fields=['user', 'session_key', 'coupon'])
        return

    user_cart.coupon = None
    user_cart.save(update_fields=['coupon'])

    anon_items = anon_cart.cart_items.select_related('product').select_for_update(of=('self', 'product'))

    for item in anon_items:
        available_quantity = max(0, item.product.quantity - item.product.reserved_quantity)
        if available_quantity <= 0:
            continue

        cart_item, created = CartItem.objects.select_for_update().get_or_create(
            cart=user_cart,
            product=item.product,
            defaults={'quantity': min(item.quantity, available_quantity)},
        )

        if not created:
            total_quantity = cart_item.quantity + item.quantity
            cart_item.quantity = min(total_quantity, available_quantity)
            cart_item.save(update_fields=['quantity'])
    
    anon_cart.delete()
