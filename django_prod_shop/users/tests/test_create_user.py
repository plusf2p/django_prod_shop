from django.test import TestCase
from django.contrib.auth import get_user_model

from django_prod_shop.users.models import Profile


class UserCreateTest(TestCase):
    def test_create_profile_after_create_user_by_command(self):
        user_model = get_user_model()
        new_user = user_model.objects.create_user(email='test_user@mail.ru', password='12345678')
        new_user.save()

        new_profile = Profile.objects.get(user=new_user)
        self.assertEqual(new_user.username, new_profile.user.username)
