from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "django_prod_shop.users"
    verbose_name = _("Users")

    def ready(self):
        from . import signals
