from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Cart, CartItem


def delete_cart_cache_by_key(cart):
    if cart.user_id:
        cache.delete(f'cart_list_user_{cart.user_id}')
    elif cart.session_key:
        cache.delete(f'cart_list_session_{cart.session_key}')


@receiver([post_save, post_delete], sender=Cart, dispatch_uid='delete_cart_cache')
def delete_cart_cache(sender, instance, **kwargs):
    delete_cart_cache_by_key(instance)


@receiver([post_save, post_delete], sender=CartItem, dispatch_uid='delete_cart_item_cache')
def delete_cart_item_cache(sender, instance, **kwargs):
    delete_cart_cache_by_key(instance.cart)
