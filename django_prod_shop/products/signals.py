from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from .models import Category, Product


@receiver([post_save, post_delete], sender=Product, dispatch_uid='delete_product_cache')
def delete_product_cache(sender, instance, **kwargs):
    cache.delete_pattern('*product_list*')
    cache.delete_pattern('*product_detail*')


@receiver([post_save, post_delete], sender=Category, dispatch_uid='delete_category_cache')
def delete_category_cache(sender, instance, **kwargs):
    cache.delete_pattern('*category_list*')
    cache.delete_pattern('*category_detail*')
