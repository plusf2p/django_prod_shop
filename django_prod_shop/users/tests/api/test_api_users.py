from django.contrib.auth import get_user_model
from django.urls import reverse

from django_prod_shop.users.models import Profile

from rest_framework import status
from rest_framework.test import APITestCase


class UsersAPISessionTest(APITestCase):
    def setUp(self):
        # Регистрация обычного пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        response1 = self.client.post(reverse('users:register'), data=self.normal_user_data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Регистрация админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password1': 'adminadmin',
            'password2': 'adminadmin',
        }
        response2 = self.client.post(reverse('users:register'), data=self.admin_user_data)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Получение профилей для будущего обращения к ним
        self.normal_profile = Profile.objects.get(user__email=self.normal_user_data['email'])
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])

        # Назначение пользователя админ правами
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        
    def test_get_partial_users_by_anon_user(self):
        # Получение чужой записи анонимно
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_partial_users_by_normal_user(self):
        # Получение своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение чужой записи, будучи авторизованным
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_partial_users_by_admin_user(self):
        # Получение своей записи, будучи админом
        self.client.login(
            email=self.admin_user_data.get('email'), password=self.admin_user_data.get('password1')
        )
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение чужой модели, будучи админом
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_update_users_by_normal_user(self):
        # Ошибочное полное обновление своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        new_wrong_normal_user_data = {
            'email': 'test_wrong_email@mail.ru',
            'full_name': '',
            'phone': '+8800553535',
            'city': 'Moscow',
            'address': 'Gagarina 14',
        }
        response = self.client.put(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}), data=new_wrong_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Правильное полное обновление своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        new_normal_user_data = {
            'full_name': 'Test Name',
            'phone': '+8800553535',
            'city': 'Moscow',
            'address': 'Gagarina 14',
        }
        response = self.client.put(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Частичтное обновление чужой записи, будучи авторизованным
        response = self.client.put(reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_patch_update_users_by_normal_user(self):
        # Ошибочное частичное обновление своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        new_wrong_normal_user_data = {
            'email': 'test_wrong_email@mail.ru',
            'full_name': '',
            'phone': '+8800553535',
            'city': 'Moscow',
            'address': 'Gagarina 14',
        }
        response = self.client.patch(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}), data=new_wrong_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Правильное частичное обновление своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        new_normal_user_data = {
            'full_name': 'Test Name',
            'phone': '+8800553535',
            'city': 'Moscow',
            'address': 'Gagarina 14',
        }
        response = self.client.patch(reverse('users:profile-detail', kwargs={'pk': self.normal_profile.pk}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Частичное обновление чужой записи, будучи авторизованным
        response = self.client.patch(reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UsersAPIJWTTest(APITestCase):
    def setUp(self):
        # Регистрация обычного пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        response1 = self.client.post(reverse('users:register'), data=self.normal_user_data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Регистрация админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password1': 'adminadmin',
            'password2': 'adminadmin',
        }
        response2 = self.client.post(reverse('users:register'), data=self.admin_user_data)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Получение профилей для будущего обращения к ним
        self.normal_profile = Profile.objects.get(user__email=self.normal_user_data['email'])
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])

        # Назначение пользователя админ правами
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
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
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })

        # Проверка логина
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'access')
        self.assertContains(response, 'refresh')
        access_token = response.data.get('access')

        # Получение своего профиля
        response = self.client.get(
            reverse('users:profile-detail', kwargs={'pk': self.admin_profile.pk}),
            headers={'Authorization': f'Bearer {access_token}'},
        )
        # Проверка своего профиля
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.admin_user_data.get('email'))

        # Получение чужого профиля
        response = self.client.get(
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
