import uuid

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Product, Category


class PaymentAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('create_groups')

    def setUp(self):
        self.client = APIClient()
        self.anon_client = APIClient()
        self.admin_client = APIClient()

        ### Users ####

        # Регистрация пользователей
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        self.client.post(reverse('users:register'), data=self.normal_user_data)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        self.access_token = response.data.get('access')
        
        # Создание админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password1': 'admin12345',
            'password2': 'admin12345',
        }
        self.admin_client.post(reverse('users:register'), data=self.admin_user_data)

        # Назначение пользователя админ правами
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
        admin_group = Group.objects.get(name='Admin')
        admin_user.groups.add(admin_group)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        # Логин админа
        response = self.admin_client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })
        self.access_token_admin = response.data.get('access')
        
        ### Products ###

        # Создание стартовой категории
        self.category = Category.objects.create(
            title='Test category', description='test description', slug='test-category'
        )
        
        # Создание двух стартовых товаров
        self.product1 = Product.objects.create(
            title='Test title of first product', category=self.category, quantity=50, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=400, sell_counter=50, is_active=True,
        )
        self.product2 = Product.objects.create(
            title='Test title of second product', category=self.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=200, sell_counter=0, is_active=True,
        )

        ### Cart ###

        # Создание запроса с товарами
        self.product_data = {
            'product_slug': self.product1.slug,
            'quantity': 10,
        }
        self.product_data_2 = {
            'product_slug': self.product2.slug,
            'quantity': 15,
        }

        # Добавление товаров в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data_2, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Добавление товаров в корзину анонимно
        response = self.anon_client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data
        )
        response = self.anon_client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data_2
        )

        ### Orders ###

        # Создание заказа
        self.order_data = {
            'full_name': 'Ildar Bbb',
            'address': 'Gagarina 20',
            'city': 'Moscow',
            'phone': '+88005553535',
        }

        # Cоздание заказа обычным пользователем
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.order_id = response.data.get('order_id')

        # Получение заказа обычным пользователем
        response = self.client.get(
            reverse('orders:orders-detail', kwargs={'order_id': self.order_id}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )

    def test_wrong_create_payment_by_anon_and_normal_user(self):
        # Неправильная попытка создать платеж анонимно и проверка
        response = self.anon_client.post(reverse('payment:payment-create', kwargs={'order_id': self.order_id}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильный order id
        wrong_order_id = uuid.uuid4()

        # Неправильная попытка создать платеж обычным пользователем и проверка
        response = self.client.post(
            reverse('payment:payment-create', kwargs={'order_id': wrong_order_id}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_wrong_get_payment_by_anon_and_normal_user(self):
        # Неправильная попытка получить один платеж анонимно и проверка
        response = self.anon_client.get(reverse('payment:payment-detail', kwargs={'id': self.order_id}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильная попытка получить список платежей анонимно и проверка
        response = self.anon_client.get(reverse('payment:payment-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильная попытка получить список платежей обычыни пользователем и проверка
        response = self.client.get(
            reverse('payment:payment-list'), headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_right_create_payment_and_get_it_by_normal_and_admin_user(self):
        # Правильная попытка создать платеж обычнм пользователем и проверка
        response = self.client.post(
            reverse('payment:payment-create', kwargs={'order_id': self.order_id}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        payment_pk = response.data['id']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Попытка получить платеж обычным пользователем
        response = self.client.get(
            reverse('payment:payment-detail', kwargs={'id': payment_pk}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Попытка получить чужой платеж админом
        response = self.admin_client.get(
            reverse('payment:payment-detail', kwargs={'id': payment_pk}),
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Попытка получить списко платежей админом
        response = self.admin_client.get(
            reverse('payment:payment-list'), headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
