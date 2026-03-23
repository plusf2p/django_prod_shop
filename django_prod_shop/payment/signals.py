from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from .models import Payment


@receiver([post_save, post_delete], sender=Payment, dispatch_uid='delete_payment_cache')
def delete_payment_cache(sender, instance, **kwargs):
    cache.delete_pattern('*payment_list*')
    cache.delete_pattern('*payment_retrieve*')
