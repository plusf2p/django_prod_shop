from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Product, Category


class CartAPITest(APITestCase):
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

        # Добавление товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Добавление товара в корзину админом
        response = self.admin_client.post(
            reverse('cart:cart-add-to-cart'), data=self.product_data_2, headers={'Authorization': f'Bearer {self.access_token_admin}'}
        )

        ### Orders ###

        # Создание заказа
        self.order_data = {
            'full_name': 'Ildar Bbb',
            'address': 'Gagarina 20',
            'city': 'Moscow',
            'phone': '+88005553535',
            'discount': 50,
        }

        # Создание статуса для заказа
        self.status_data = {
            'status': 'delivered'
        }

        ### Reviews ###

        self.reivew_data_1 = {
            'product': self.product1.slug,
            'comment': 'Test comment 1',
            'rating': 4,
        }

        self.reivew_data_2 = {
            'product': self.product2.slug,
            'comment': 'Test comment 2',
            'rating': 3,
        }
    
    def test_wrong_create_review_without_delivery_product_status_by_anon_and_normal_users(self):
        # Неправильная попытка создать отзыв (без доставленного товара) анонимно с правильными данными и проверка
        response = self.anon_client.post(reverse('reviews:reviews-list'), data=self.reivew_data_1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильная попытка создать отзыв (без доставленного товара) обычным пользователем 
        # с правильными данными и проверка
        response = self.client.post(
            reverse('reviews:reviews-list'), data=self.reivew_data_1, 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_right_create_review__and_get_it_by_normal_and_admin_users(self):
        # Создание заказа обычным пользователем
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data,
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        order_id = response.data.get('order_id')

        # Создание заказа админом
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data, 
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        order_id_admin = response.data.get('order_id')

        # Изменение статуса заказов админом
        response = self.admin_client.post(
            reverse('orders:change_order_status', kwargs={'order_id': order_id}), 
            data=self.status_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        response = self.admin_client.post(
            reverse('orders:change_order_status', kwargs={'order_id': order_id_admin}), 
            data=self.status_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )

        # Правильная попытка создать отзыв обычным пользователем с правильными данными и проверка
        response = self.client.post(
            reverse('reviews:reviews-list'), data=self.reivew_data_1, 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review_id = response.data.get('id')

        # Попытка получить созданный отзыв обычным пользователем по id и проверка
        response = self.client.get(
            reverse('reviews:reviews-detail', kwargs={'id': review_id}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comment'], self.reivew_data_1.get('comment'))

        # Правильная попытка создать отзыв админом с правильными данными и проверка
        response = self.admin_client.post(
            reverse('reviews:reviews-list'), data=self.reivew_data_2, 
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review_id = response.data.get('id')

        # Попытка получить созданный отзыв обычным пользователем по id и проверка
        response = self.admin_client.get(
            reverse('reviews:reviews-detail', kwargs={'id': review_id}), 
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comment'], self.reivew_data_2.get('comment'))
