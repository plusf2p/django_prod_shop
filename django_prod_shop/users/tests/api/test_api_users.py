from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase


class UsersAPISessionTest(APITestCase):
    def setUp(self):
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        response1 = self.client.post(reverse('users:register'), data=self.normal_user_data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password1': 'adminadmin',
            'password2': 'adminadmin',
        }
        response2 = self.client.post(reverse('users:register'), data=self.admin_user_data)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
    
    def test_get_partial_users_by_anon_user(self):
        # Получение чужой записи анонимно
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_partial_users_by_normal_user(self):
        # Получение своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение чужой записи, будучи авторизованным
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': 2}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_partial_users_by_admin_user(self):
        # Получение своей записи, будучи админом
        self.client.login(
            email=self.admin_user_data.get('email'), password=self.admin_user_data.get('password1')
        )
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': 2}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение чужой модели, будучи админом
        response = self.client.get(reverse('users:profile-detail', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_update_users_by_normal_user(self):
        # Ошибочное полное обновление своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        new_wrong_normal_user_data = {
            'email': 'test_wrong_email@mail.ru',
            'full_name': 'Test Name',
            'phone': '+8800553535',
            'city': 'Moscow',
            'address': 'Gagarina 14',
        }
        response = self.client.put(reverse('users:profile-detail', kwargs={'pk': 1}), data=new_wrong_normal_user_data)
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
        response = self.client.put(reverse('users:profile-detail', kwargs={'pk': 1}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Частичтное обновление чужой записи, будучи авторизованным
        response = self.client.put(reverse('users:profile-detail', kwargs={'pk': 2}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_patch_update_users_by_normal_user(self):
        # Ошибочное частичное обновление своей записи, будучи авторизованным
        self.client.login(
            email=self.normal_user_data.get('email'), password=self.normal_user_data.get('password1')
        )
        new_wrong_normal_user_data = {
            'email': 'test_wrong_email@mail.ru',
            'full_name': 'Test Name',
            'phone': '+8800553535',
            'city': 'Moscow',
            'address': 'Gagarina 14',
        }
        response = self.client.patch(reverse('users:profile-detail', kwargs={'pk': 1}), data=new_wrong_normal_user_data)
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
        response = self.client.patch(reverse('users:profile-detail', kwargs={'pk': 1}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Частичное обновление чужой записи, будучи авторизованным
        response = self.client.patch(reverse('users:profile-detail', kwargs={'pk': 2}), data=new_normal_user_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
