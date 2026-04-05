from unittest.mock import patch
import re

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.users.models import Profile


user_model = get_user_model()


class UsersAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        # Создание ролей
        call_command('create_groups')

        # Объявление url
        cls.register_url = reverse('users:register')
        cls.activation_url = reverse('users:user-activation')
        cls.resend_activation_url = reverse('users:user-resend-activation')
        cls.token_create_url = reverse('users:token-access')
        cls.token_refresh_url = reverse('users:token-refresh')
        cls.reset_password_url = reverse('users:user-reset-password')
        cls.reset_password_confirm_url = reverse('users:user-reset-password-confirm')

    def setUp(self):
        self.admin_client = APIClient()
        self.sent_emails = []

        # Замена функций для пропуска тасков
        self.on_commit_patcher = patch(
            'django_prod_shop.users.emails.transaction.on_commit',
            side_effect=lambda callback: callback(),
        )
        self.delay_patcher = patch(
            'django_prod_shop.users.emails.send_email_task.delay',
            side_effect=self.fake_send_email,
        )

        # Активация замен
        self.on_commit_patcher.start()
        self.delay_patcher.start()
        # Выключение замен после конца работы тестов
        self.addCleanup(self.on_commit_patcher.stop)
        self.addCleanup(self.delay_patcher.stop)

        # Создание обычного пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password': 'test_user1_password!',
            're_password': 'test_user1_password!',
        }

        # Создание админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password': 'admin_password!',
            're_password': 'admin_password!',
        }

    def fake_send_email(self, subject, body, to):
        # "Отправка" email вместо отправки в таске
        self.sent_emails.append({
            'subject': subject,
            'body': body,
            'to': to,
        })

    def get_uid_and_token(self, body, url_part):
        # Взятие uid и token из "письма"
        pattern = rf'{url_part}/(?P<uid>[^/]+)/(?P<token>[^/\s]+)/'
        match = re.search(pattern, body)
        self.assertIsNotNone(match, msg=f'Не удалось найти uid/token в письме:\n\n{body}')
        return match.group('uid'), match.group('token')

    def register_user(self, user_data):
        # Регистрация пользователя
        response = self.client.post(self.register_url, data=user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def activate_user_from_last_email(self):
        # Проверка и взятем uid и token из письма
        self.assertGreater(len(self.sent_emails), 0, msg='Нет писем для активации')
        body = self.sent_emails[-1]['body']
        uid, token = self.get_uid_and_token(body, 'activate')

        # Активиция пользователя
        response = self.client.post(
            self.activation_url,
            data={
                'uid': uid,
                'token': token,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        return response

    def login_user(self, email, password, client=None):
        # Логин пользователя
        if client is None:
            client = self.client
        
        response = client.post(
            self.token_create_url,
            data={
                'email': email,
                'password': password,
            },
            format='json',
        )
        return response

    def auth_header_client(self, client, access_token):
        # Добавление Authorization к запросу
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_register_in_active_user_and_send_activation_email(self):
        # Регистрация пользователя и проверка
        response = self.register_user(self.normal_user_data)
        self.assertEqual(response.data['email'], self.normal_user_data['email'])
        self.assertNotIn('password', response.data)

        # Получение пользователя и проврека активности
        user = user_model.objects.get(email=self.normal_user_data['email'])
        self.assertFalse(user.is_active)

        # Проверка на наличие "письма"
        self.assertEqual(len(self.sent_emails), 1)
        self.assertEqual(self.sent_emails[0]['to'], [self.normal_user_data['email']])

    def test_activate_user_by_email_and_login_with_jwt(self):
        # Регистрация пользователя
        self.register_user(self.normal_user_data)

        # Получение пользователя и проврека активности
        user = user_model.objects.get(email=self.normal_user_data['email'])
        self.assertFalse(user.is_active)

        # Неправильный логин (без активации) и проверка
        login_before_activation = self.login_user(
            self.normal_user_data['email'],
            self.normal_user_data['password'],
        )
        self.assertEqual(login_before_activation.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Активация после "отправки письма"
        self.activate_user_from_last_email()
        
        # Рефреш базы данных и проврека активности
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # Правильный логин и проверка
        login_response = self.login_user(
            self.normal_user_data['email'],
            self.normal_user_data['password'],
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)

    def test_resend_activation_email(self):
        # Регистрация пользователя
        self.register_user(self.normal_user_data)

        # Переотправка "письима" и проврека "письма"
        response = self.client.post(
            self.resend_activation_url,
            data={'email': self.normal_user_data['email']},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(self.sent_emails), 2)
        self.assertEqual(self.sent_emails[-1]['to'], [self.normal_user_data['email']])
        self.assertIn('/activate/', self.sent_emails[-1]['body'])

    def test_refresh_jwt_token(self):
        # Регистрация обычного полльзователя
        self.register_user(self.normal_user_data)

        # Активация обычного пользователя
        self.activate_user_from_last_email()

        # Логин обычного пользователя и проврека
        login_response = self.login_user(
            self.normal_user_data['email'],
            self.normal_user_data['password'],
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)
        self.assertIn('refresh', login_response.data)

        # Рефреш JWT токена и проверка
        refresh_response = self.client.post(
            self.token_refresh_url,
            data={'refresh': login_response.data['refresh']},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
        self.assertNotIn('refresh', refresh_response.data)

    def test_normal_user_can_get_only_his_own_profile(self):
        # Регистрация обычного и админ пользователей
        self.register_user(self.normal_user_data)
        self.register_user(self.admin_user_data)

        # Получение обычного и админ пользователей
        normal_user = user_model.objects.get(email=self.normal_user_data['email'])
        admin_user = user_model.objects.get(email=self.admin_user_data['email'])

        # Активация обычного пользователя
        normal_user.is_active = True
        normal_user.save(update_fields=['is_active'])

        # Активация админа и назначение суперюзером
        admin_user.is_active = True
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save(update_fields=['is_active', 'is_staff', 'is_superuser'])

        # Получение профилей обычного и админ пользователей
        normal_profile = Profile.objects.get(user=normal_user)
        admin_profile = Profile.objects.get(user=admin_user)

        # Логин обычного пользователя и проверка
        login_response = self.login_user(
            self.normal_user_data['email'],
            self.normal_user_data['password'],
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Получение своего профиля обычным пользователем и проверка
        normal_user_profile_response = self.client.get(
            reverse('profile:profile-detail', kwargs={'pk': normal_profile.pk})
        )
        self.assertEqual(normal_user_profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(normal_user_profile_response.data['email'], self.normal_user_data['email'])

        # Получение чужого профиля обычным пользователем и проверка
        admin_profile_response = self.client.get(
            reverse('profile:profile-detail', kwargs={'pk': admin_profile.pk})
        )
        self.assertEqual(admin_profile_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_get_other_users_profile(self):
        # Регистрация обычного и админ пользователей
        self.register_user(self.normal_user_data)
        self.register_user(self.admin_user_data)

        # Получение обычного и админ пользователей
        normal_user = user_model.objects.get(email=self.normal_user_data['email'])
        admin_user = user_model.objects.get(email=self.admin_user_data['email'])

        # Активация обычного пользователя
        normal_user.is_active = True
        normal_user.save(update_fields=['is_active'])

        # Активация админа и назвачение суперюзером
        admin_user.is_active = True
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save(update_fields=['is_active', 'is_staff', 'is_superuser'])

        # Получение профилей обычного и админ пользователей
        normal_profile = Profile.objects.get(user=normal_user)
        admin_profile = Profile.objects.get(user=admin_user)

        # Логин админа и проверка
        login_response = self.login_user(
            self.admin_user_data['email'],
            self.admin_user_data['password'],
            client=self.admin_client,
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Получение своего профиля админом и проверка
        admin_profile_response = self.admin_client.get(
            reverse('profile:profile-detail', kwargs={'pk': admin_profile.pk})
        )
        self.assertEqual(admin_profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_profile_response.data['email'], self.admin_user_data['email'])

        # Получение чужого профиля админом и проверка
        normal_user_profile_response = self.admin_client.get(
            reverse('profile:profile-detail', kwargs={'pk': normal_profile.pk})
        )
        self.assertEqual(normal_user_profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(normal_user_profile_response.data['email'], self.normal_user_data['email'])

    def test_password_reset_by_email_and_login_with_new_password(self):
        # Регистрация обычного пользователя
        self.register_user(self.normal_user_data)
        
        # Активация обычного пользователя
        self.activate_user_from_last_email()

        # Восстановление пароля обычного пользователя и проверка
        response = self.client.post(
            self.reset_password_url,
            data={'email': self.normal_user_data['email']},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка "письма" для восстановления пароля
        self.assertEqual(len(self.sent_emails), 2)
        reset_email = self.sent_emails[-1]
        self.assertEqual(reset_email['to'], [self.normal_user_data['email']])
        self.assertIn('/password-reset-confirm/', reset_email['body'])

        # Получение uid и token из "письма" для восстановления пароля
        uid, token = self.get_uid_and_token(reset_email['body'], 'password-reset-confirm')

        # Новый пароль
        new_password = 'NewTestPassword123!'

        # Смена пароля на новый и проверка
        confirm_response = self.client.post(
            self.reset_password_confirm_url,
            data={
                'uid': uid,
                'token': token,
                'new_password': new_password,
                're_new_password': new_password,
            },
            format='json',
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_204_NO_CONTENT)

        # Попытка лоигна со старым паролем и проврека
        old_login_response = self.login_user(
            self.normal_user_data['email'],
            self.normal_user_data['password'],
        )
        self.assertEqual(old_login_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Логин с новым паролем и проврека
        new_login_response = self.login_user(
            self.normal_user_data['email'],
            new_password,
        )
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', new_login_response.data)
        self.assertIn('refresh', new_login_response.data)

    def test_wrong_password_reset_confirm(self):
        # Регистрация обычного пользоателя
        self.register_user(self.normal_user_data)

        # Активация обычного пользователя
        self.activate_user_from_last_email()

        # Неправильное восстановление пароля и проверка
        response = self.client.post(
            self.reset_password_confirm_url,
            data={
                'uid': 'wrong_uid',
                'token': 'wrong_token',
                'new_password': 'test_user_password!',
                're_new_password': 'test_user_password!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
