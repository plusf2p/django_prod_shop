from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.products.models import Category, Product


user_model = get_user_model()


class CartAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        # Создание ролей
        call_command('create_groups')
        
        ### Users ####

        # Создание обычного пользователя
        cls.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password': 'test_user1_password!',
        }
        user_model.objects.create_user(
            email=cls.normal_user_data['email'], 
            password=cls.normal_user_data['password'],
            is_active=True,
        )

        # Создание админа (суперюзера)
        cls.admin_user_data = {
            'email': 'admin@mail.ru',
            'password': 'admin_password!',
        }
        user_model.objects.create_superuser(
            email=cls.admin_user_data['email'], 
            password=cls.admin_user_data['password'],
            is_active=True,
        )

        # Объявление url
        cls.token_create_url = reverse('users:token-access')
        cls.cart_list_url = reverse('cart:cart-list')
        cls.add_to_cart_url = reverse('cart:cart-add-to-cart')
        cls.clear_cart_url = reverse('cart:cart-clear-cart')

        ### Products ###

        # Создание стартовой категории
        cls.category = Category.objects.create(
            title='Test category', description='test description', slug='test-category'
        )
        
        # Создание двух стартовых товаров
        cls.product1 = Product.objects.create(
            title='Test title of first product', category=cls.category, quantity=10, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=400, is_active=True,
        )
        cls.product2 = Product.objects.create(
            title='Test title of second product', category=cls.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=200, is_active=True,
        )

    def setUp(self):
        self.admin_client = APIClient()
        self.anon_client = APIClient()
    
    def get_cart_update_url_with_kwargs(self, kwargs=None):
        return reverse('cart:cart-update-cart-item', kwargs=kwargs)
    
    def get_cart_remove_url_with_kwargs(self, kwargs=None):
        return reverse('cart:cart-remove-cart-item', kwargs=kwargs)
    
    def add_to_cart_test_product(self, client=None):
        # Добавление тестового товара в корзину
        if client is None:
            client = self.client

        test_product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        test_response = client.post(
            self.add_to_cart_url, data=test_product_data
        )
        self.assertEqual(test_response.status_code, status.HTTP_200_OK)

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

    def test_get_empty_cart_by_anon_and_normal_users(self):
        # Получение пустой корзины анонимно и проверка
        cart_anon_response = self.anon_client.get(self.cart_list_url)
        self.assertEqual(cart_anon_response.status_code, status.HTTP_200_OK)

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Получение пустой корзины обычным пользователем и проверка
        cart_normal_response = self.client.get(
            self.cart_list_url,
        )
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)
    
    def test_add_to_cart_right_products_and_get_it_by_anon_and_normal_users(self):
        # Данные товаров для добавления в корзину
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }
        product_data_2 = {
            'product_slug': self.product2.slug,
            'qauntity': 1,
        }
        
        # Добавление товаров в корзину анонимно и проверка
        add_to_cart_anon_response = self.anon_client.post(
            self.add_to_cart_url, data=product_data,
        )
        self.assertEqual(add_to_cart_anon_response.status_code, status.HTTP_200_OK)
        add_to_cart_anon_response = self.anon_client.post(
            self.add_to_cart_url, data=product_data_2,
        )
        self.assertEqual(add_to_cart_anon_response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно
        cart_anon_response = self.anon_client.get(self.cart_list_url)

        # Проверка корзины анонимно
        self.assertEqual(cart_anon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_anon_response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(cart_anon_response.data['items'][1]['product_title'], self.product2.title)
        self.assertEqual(cart_anon_response.data['items'][0]['quantity'], product_data['quantity'])

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Получение пустой корзины обычным пользователем и проверка
        cart_normal_response = self.client.get(self.cart_list_url)
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)

        # Добавление товаров в корзину обычным пользователем и проверка
        add_to_cart_normal_response = self.client.post(
            self.add_to_cart_url, data=product_data,
        )
        self.assertEqual(add_to_cart_normal_response.status_code, status.HTTP_200_OK)
        add_to_cart_normal_response = self.client.post(
            self.add_to_cart_url, data=product_data_2,
        )
        self.assertEqual(add_to_cart_normal_response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем
        cart_normal_response = self.client.get(self.cart_list_url)

        # Провкерка корзины обычным пользователем
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_normal_response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(cart_normal_response.data['items'][1]['product_title'], self.product2.title)
        self.assertEqual(cart_normal_response.data['items'][0]['quantity'], product_data['quantity'])

    def test_add_to_cart_over_products_and_get_cart_by_admin_user(self):
        # Неправильные данные для доьавления товара в корзину
        product_data_over = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }

        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
            client=self.admin_client,
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Добавление неправильного количества товара в корзину админом и проверка
        wrong_admin_response = self.admin_client.post(
            self.add_to_cart_url, data=product_data_over,
        )
        self.assertEqual(wrong_admin_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины админом
        cart_admin_response = self.admin_client.get(self.cart_list_url)
        
        # Проверка корзины админом
        self.assertEqual(cart_admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_admin_response.data['items'], [])

    def test_add_to_cart_products_and_right_update_it_and_get_cart_by_anon_user(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)
        
        # Получение item_id
        item_id = self.anon_client.get(self.cart_list_url).data['items'][0]['id']

        # Обновлнение на правильное количество анонимно и проверка
        cart_update_anon_response = self.anon_client.patch(
           self.get_cart_update_url_with_kwargs(kwargs={'item_id': item_id}), 
           data={'quantity': 2},
        )
        self.assertEqual(cart_update_anon_response.status_code, status.HTTP_200_OK)
    
        # Получение корзины анонимно после обновления
        cart_anon_response = self.anon_client.get(self.cart_list_url)

        # Проверка корзины анонимно после обновления
        self.assertEqual(cart_anon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_anon_response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(cart_anon_response.data['items'][0]['quantity'], 2)

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()
        
        # Получение item_id
        item_id = self.client.get(self.cart_list_url).data['items'][0]['id']

        # Обновлнение на правильное количество обычным пользователем и проверка
        cart_update_normal_response = self.client.patch(
           self.get_cart_update_url_with_kwargs(kwargs={'item_id': item_id}), 
           data={'quantity': 2},
        )
        self.assertEqual(cart_update_normal_response.status_code, status.HTTP_200_OK)
    
        # Получение корзины обычным пользователем после обновления
        cart_normal_response = self.client.get(self.cart_list_url)

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_normal_response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(cart_normal_response.data['items'][0]['quantity'], 2)

    def test_add_to_cart_products_and_right_remove_it_and_get_cart_by_anon_and_normal_users(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Получение item_id
        item_id = self.anon_client.get(self.cart_list_url).data['items'][0]['id']

        # Удаление из корзины анонимно и проверка
        delete_anon_response = self.anon_client.delete(
            self.get_cart_remove_url_with_kwargs(kwargs={'item_id': item_id}),
        )
        self.assertEqual(delete_anon_response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно после удаления
        deleted_anon_response = self.anon_client.get(self.cart_list_url)

        # Проверка корзины анонимно после удаления
        self.assertEqual(deleted_anon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted_anon_response.data['items'], [])

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()

        # Получение item_id
        item_id = self.client.get(self.cart_list_url).data['items'][0]['id']

        # Удаление из корзины обычным пользователем и проверка
        delete_normal_response = self.client.delete(
            self.get_cart_remove_url_with_kwargs(kwargs={'item_id': item_id}),
        )
        self.assertEqual(delete_normal_response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем после удаления
        deleted_normal_response = self.client.get(self.cart_list_url)

        # Проверка корзины обычным пользователем после удаления
        self.assertEqual(deleted_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted_normal_response.data['items'], [])

    def test_add_to_cart_products_and_wrong_remove_it_and_get_it_by_anon_and_normal_users(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Неправильное удаление из корзины анонимно и проверка
        wrong_anon_response = self.anon_client.delete(
            self.get_cart_remove_url_with_kwargs(kwargs={'item_id': 50}),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение корзины анонимно после удаления
        cart_anon_response = self.anon_client.get(self.cart_list_url)

        # Проверка корзины анонимно после удаления
        self.assertEqual(cart_anon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_anon_response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(cart_anon_response.data['items'][0]['quantity'], 1)

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()

        # Неправильное удаление из корзины обычным пользователем и проверка
        wrong_normal_response = self.client.delete(
            self.get_cart_remove_url_with_kwargs(kwargs={'item_id': 50}),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение корзины обычным пользователем после удаления
        cart_normal_response = self.client.get(self.cart_list_url)

        # Проверка корзины обычным пользователем после удаления
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_normal_response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(cart_normal_response.data['items'][0]['quantity'], 1)

    def test_clear_cart_by_anon_and_normal_users(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Очистка корзины анонимно
        cart_clear_anon_response = self.anon_client.delete(self.clear_cart_url)
        self.assertEqual(cart_clear_anon_response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины анонимно после очистки
        cart_anon_response = self.anon_client.get(self.cart_list_url)
        
        # Проверка корзины анонимно после очистки
        self.assertEqual(cart_anon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_anon_response.data['items'], [])
        
        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()

        # Очистка корзины обычным пользователем
        cart_clear_normal_response = self.client.delete(self.clear_cart_url)
        self.assertEqual(cart_clear_normal_response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины обычным пользователем после очистки
        cart_normal_response = self.client.get(self.cart_list_url)

        # Проверка корзины обычным пользователем после очистки
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_normal_response.data['items'], [])
        
    def test_merge_cart_by_anon_to_normal_user(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Логин и мердж корзины обычным анонимом (теперь уже обычным пользователем)
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
            client=self.anon_client,
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Проверка старой корзины анонимно
        cart_anon_response = self.anon_client.get(self.cart_list_url)
        self.assertEqual(cart_anon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_anon_response.data['items'], [])

        # Проверка новой корзины через другую сессиию обычным пользователем
        cart_normal_response = self.client.get(self.cart_list_url)
        self.assertEqual(cart_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart_normal_response.data['items'][0]['product_title'], self.product1.title)
