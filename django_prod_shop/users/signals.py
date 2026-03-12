from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User, Profile


@receiver(post_save, sender=User, dispatch_uid='create_profile')
def create_profile(sender, instance, created, **kwargs):
    if created and not instance.profile.exists():
        Profile.objects.create(
            user=instance, full_name='', phone='', city='', address='',
        )
