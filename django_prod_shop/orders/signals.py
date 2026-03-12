from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from .models import Order, OrderItem


@receiver([post_save, post_delete], sender=Order, dispatch_uid='delete_order_cache')
def delete_order_cache(sender, instance, **kwargs):
    cache.delete(f'order_retrieve_{instance.order_id}')


@receiver([post_save, post_delete], sender=OrderItem, dispatch_uid='delete_order_item_cache')
def delete_order_item_cache(sender, instance, **kwargs):
    cache.delete(f'order_retrieve_{instance.order.order_id}')
