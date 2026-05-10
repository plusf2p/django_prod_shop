from typing import Any

from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from .models import Review


@receiver([post_save, post_delete], sender=Review, dispatch_uid='delete_review_cache')
def delete_review_cache(sender: type[Review], instance: Review, **kwargs: Any) -> None:
    cache.delete_pattern('*review_list*')
    cache.delete_pattern('*review_retrieve*')


@receiver([post_save, post_delete], sender=Review, dispatch_uid='delete_review_related_cache')
def delete_review_related_cache(sender: type[Review], instance: Review, **kwargs: Any) -> None:
    cache.delete_pattern('*product_list*')
    cache.delete_pattern('*product_retrieve*')
    cache.delete_pattern('*category_retrieve*')
