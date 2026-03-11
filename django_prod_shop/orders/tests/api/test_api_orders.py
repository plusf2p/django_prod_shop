from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Product, Category


class CartAPITest(APITestCase):
    def setUp(self):
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
        self.client.post(reverse('users:register'), data=self.admin_user_data)

        # Назначение пользователя админ правами
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        # Логин админа
        response = self.client.post(reverse('users:token_access'), data={
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
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data
        )
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data_2
        )

        ### Orders ###

        self.order_data = {
            'full_name': 'Ildar Bbb',
            'address': 'Gagarina 20',
            'city': 'Moscow',
            'phone': '+88005553535',
            'discount': 50,
        }

    def test_worng_create_order_by_normal_users(self):
        # Изменение данных заказа
        order_data = self.order_data.copy()
        order_data['full_name'] = ''

        # Неправильное создание заказа обычным пользователем и проверка
        response = self.client.post(
            reverse('orders:orders-list'), data=order_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_right_create_order_and_get_it_by_anon_and_normal_users(self):
        # Cоздание заказа обычным пользователем и проверка
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data.get('order_id')

        # Получение заказа обычным пользователем
        response = self.client.get(
            reverse('orders:orders-detail', kwargs={'order_id': order_id}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        
        # Проверка заказа обычным пользователем
        self.assertEqual(response.data['items'][0]['product_slug'], self.product_data.get('product_slug'))
        self.assertEqual(response.data['items'][0]['quantity'], self.product_data.get('quantity'))
        self.assertEqual(response.data['items'][1]['product_slug'], self.product_data_2.get('product_slug'))
        self.assertEqual(response.data['items'][1]['quantity'], self.product_data_2.get('quantity'))
        
        # Получение корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Проверка корзины обычным пользователеи
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

    def test_get_all_orders_by_admin_user(self):
        # Создание заказа обычным пользователем
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Получение всех заказов админом
        response = self.client.get(
            reverse('orders:orders-list'), headers={'Authorization': f'Bearer {self.access_token_admin}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['items'][0]['product_slug'], self.product_data.get('product_slug'))
        self.assertEqual(response.data[0]['items'][1]['product_slug'], self.product_data_2.get('product_slug'))
    
    def test_change_order_status_by_normal_and_admin_users(self):
        # Создание статуса
        status_data = {
            'status': 'paid'
        }

        # Создание заказа обычным пользователем
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        order_id = response.data.get('order_id')

        # Попытка изменить статус заказа обычныи пользователем и проверка
        response = self.client.post(
            reverse('orders:change_order_status', kwargs={'order_id': order_id}), 
            data=status_data, headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Изменение заказа админом и проверка
        response = self.client.post(
            reverse('orders:change_order_status', kwargs={'order_id': order_id}), 
            data=status_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка статуса у заказа админом
        response = self.client.get(
            reverse('orders:orders-detail', kwargs={'order_id': order_id}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'paid')
