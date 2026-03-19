
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, EmailField, OneToOneField, Model, CASCADE
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for Django Shop.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class Profile(Model):
    user = OneToOneField(User, on_delete=CASCADE, verbose_name='Пользователь')
    full_name = CharField(max_length=300, verbose_name='Имя')
    phone = CharField(max_length=40, verbose_name='Телефон')
    city = CharField(max_length=100, verbose_name='Город')
    address = CharField(max_length=255, verbose_name='Адрес')

    def __str__(self):
        return f'{self.full_name} - ({self.user})'
    
    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
