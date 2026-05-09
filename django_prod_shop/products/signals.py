from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from typing import Any

from .models import Category, Product


@receiver([post_save, post_delete], sender=Product, dispatch_uid='delete_product_cache')
def delete_product_cache(sender: type[Product], instance: Product, **kwargs: Any) -> None:
    cache.delete_pattern('*product_list*')
    cache.delete_pattern('*product_retrieve*')


@receiver([post_save, post_delete], sender=Category, dispatch_uid='delete_category_cache')
def delete_category_cache(sender: type[Category], instance: Category, **kwargs: Any) -> None:
    cache.delete_pattern('*category_list*')
    cache.delete_pattern('*category_retrieve*')
    cache.delete_pattern('*product_list*')
    cache.delete_pattern('*product_retrieve*')
