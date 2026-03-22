from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Group


from .models import User, Profile


@receiver(post_save, sender=User, dispatch_uid='create_profile')
def create_profile(sender, instance, created, **kwargs):
    if created:
        group = Group.objects.get(name='Customer')
        instance.groups.add(group)

        Profile.objects.create(
            user=instance, full_name='', phone='', city='', address='',
        )
