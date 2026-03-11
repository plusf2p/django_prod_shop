from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

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
        
        user_model = get_user_model()
        user_model.objects.create_superuser(email='admin@admin.ru', password='admin')
        
        ### Products ###

        # Создание стартовой категории
        self.category = Category.objects.create(
            title='Test category', description='test description', slug='test-category'
        )
        
        # Создание двух стартовых товаров
        self.product1 = Product.objects.create(
            title='Test title of first product', category=self.category, quantity=10, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=400, sell_counter=50, is_active=True,
        )
        self.product2 = Product.objects.create(
            title='Test title of second product', category=self.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=200, sell_counter=0, is_active=True,
        )

        ### Cart ###

        # Создание запроса с товарами
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 10,
        }
        product_data_2 = {
            'product_slug': self.product2.slug,
            'qauntity': 15,
        }

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Добавление товаров в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data_2, headers={'Authorization': f'Bearer {access_token}'}
        )
    def test_create_order_and_get_it_by_anon_and_normal_users(self):
        
