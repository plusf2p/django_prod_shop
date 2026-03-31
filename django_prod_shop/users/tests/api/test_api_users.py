from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from django_prod_shop.users.models import Profile

from rest_framework import status
from rest_framework.test import APITestCase, APIClient


class UsersAPIJWTTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('create_groups')

    def setUp(self):
        self.admin_client = APIClient()

        # Регистрация обычного пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password': 'TestPassword123',
            're_password': 'TestPassword123',
        }
        response = self.client.post(reverse('users:register'), data=self.normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Регистрация админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password': 'TestPassword123',
            're_password': 'TestPassword123',
        }
        response2 = self.admin_client.post(reverse('users:register'), data=self.admin_user_data)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Получение профилей для будущего обращения к ним
        self.normal_profile = Profile.objects.get(user__email=self.normal_user_data['email'])
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])

        # Назначение пользователя админ правами
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
        admin_group = Group.objects.get(name='Admin')
        admin_user.groups.add(admin_group)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

    def test_login_normal_user_with_jwt_and_get_users_profile_data(self):
        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })

        # Проверка логина
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'access')
        self.assertContains(response, 'refresh')
        access_token = response.data.get('access')

        # Получение своего профиля
        response = self.client.get(
            reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        # Проверка своего профиля
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.normal_user_data.get('email'))

        # Получение чужого профиля
        response = self.client.get(
            reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_login_admin_user_with_jwt_and_get_users_profile_data(self):
        # Логин админа
        response = self.admin_client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })

        # Проверка логина
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'access')
        self.assertContains(response, 'refresh')
        access_token = response.data.get('access')

        # Получение своего профиля
        response = self.admin_client.get(
            reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        # Проверка своего профиля
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.admin_user_data.get('email'))

        # Получение чужого профиля
        response = self.admin_client.get(
            reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_jwt_token_after_login(self):
        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })

        # Проверка логина
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'access')
        self.assertContains(response, 'refresh')

        # Получение нового access токена
        response = self.client.post(reverse('users:token_refresh'), data={
            'refresh': response.data.get('refresh'),
        })

        # Проверка нового access токена
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'access')
        self.assertNotContains(response, 'refresh')

    def test_right_change_password_and_login_by_normal_user(self):
        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Новый правильный пароль
        new_password_data = {
            'old_password': self.normal_user_data.get('password1'),
            'new_password1': 'test_right_password_123',
            'new_password2': 'test_right_password_123',
        }

        # Правильная смена пароля и проверка
        response = self.client.post(
            reverse('users:change_password'), data=new_password_data,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['password'], 'Пароль успешно изменен')
        access_token = response.data.get('access')

        # Получение своего профиля с новым токеном и проверка
        response = self.client.get(
            reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Логин с новым паролем и проверка
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': new_password_data.get('new_password1'),
        })
        access_token = response.data.get('access')

        # Получение своего профиля с новым токеном после логина и проверка
        response = self.client.get(
            reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_change_password_and_login_by_normal_user(self):
        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Новый неправильный пароль (новые пароли не совпадают)
        wrong_new_password_data = {
            'old_password': self.normal_user_data.get('password1'),
            'new_password1': 'test_right_password_321',
            'new_password2': 'test_right_password_123',
        }

        # Неправильная смена пароля и проверка
        response = self.client.post(
            reverse('users:change_password'), data=wrong_new_password_data,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Новый неправильный пароль (неверный прошлый пароль)
        wrong_new_password_data = {
            'old_password': '123',
            'new_password1': 'test_right_password_123',
            'new_password2': 'test_right_password_123',
        }

        # Неправильная смена пароля и проверка
        response = self.client.post(
            reverse('users:change_password'), data=wrong_new_password_data,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
