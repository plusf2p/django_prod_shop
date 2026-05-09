from typing import Any

from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver

from .models import Coupon


@receiver([post_save, post_delete], sender=Coupon, dispatch_uid='delete_coupon_cache')
def delete_coupon_cache(sender: type[Coupon], instance: Coupon, **kwargs: Any) -> None:
    cache.delete_pattern('*coupon_list*')
    cache.delete_pattern('*coupon_retrieve*')
