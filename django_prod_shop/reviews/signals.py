from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from .models import Review


@receiver([post_save, post_delete], sender=Review, dispatch_uid='delete_review_cache')
def delete_review_cache(sender, instance, **kwargs):
    cache.delete_pattern('*review_list*')
    cache.delete_pattern('*review_retrieve*')
