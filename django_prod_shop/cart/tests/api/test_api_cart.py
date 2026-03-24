from django.urls import reverse
from django.core.management import call_command

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.products.models import Product, Category


class CartAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('create_groups')

    def setUp(self):
        self.client = APIClient()
        self.anon_client = APIClient()

        ### Users ####

        # Регистрация пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        self.client.post(reverse('users:register'), data=self.normal_user_data)

        # Логин обычного пользователя и проверка
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        self.access_token = response.data.get('access')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
    
    def test_get_empty_cart_by_anon_and_normal_users(self):
        # Получение пустой корзины анонимно
        response = self.anon_client.get(reverse('cart:cart-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_add_to_cart_right_products_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товарами
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }
        product_data_2 = {
            'product_slug': self.product2.slug,
            'qauntity': 1,
        }

        
        # Добавление товаров в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data_2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно
        response = self.anon_client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(response.data['items'][1]['product_title'], self.product2.title)
        self.assertEqual(response.data['items'][0]['quantity'], product_data.get('quantity'))

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Добавление товаров в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data_2, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Провкерка корзины обычным пользователем
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(response.data['items'][1]['product_title'], self.product2.title)
        self.assertEqual(response.data['items'][0]['quantity'], product_data.get('quantity'))

    def test_add_to_cart_over_products_and_get_it_by_anon_and_normal_users(self):
        # Добавление неправильного количества товара в корзину
        product_data_over = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }
        
        # Добавление неправильного количества товара в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data_over)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины анонимно
        response = self.anon_client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

        # Добавление неправильного количества товара в корзину
        product_data_over = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }

        # Добавление неправильного количества товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data_over, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины обычным пользователем
        response = self.client.get(reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'})
        
        # Проверка корзины обычным пользователем
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])
    
    def test_add_to_cart_products_and_right_update_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)

        # Получение корзины анонимно
        response = self.anon_client.get(reverse('cart:cart-list'))
        
        # Получение item_id
        item_id = self.anon_client.get(reverse('cart:cart-list')).data['items'][0]['id']

        # Обновлнение на правильное количество анонимно
        response = self.anon_client.patch(
            reverse('cart:cart-update-cart-item', kwargs={'item_id': item_id}), data={'quantity': 2}
        )
        
        # Проверка запроса
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно после обновления
        response = self.anon_client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(response.data['items'][0]['quantity'], 2)

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'),headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Получение item_id
        item_id = self.client.get(reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}).data['items'][0]['id']

        # Обновлнение на правильное количество обычным пользователем
        response = self.client.patch(
            reverse('cart:cart-update-cart-item', kwargs={'item_id': item_id}), 
            data={'quantity': 2}, headers={'Authorization': f'Bearer {self.access_token}'},
        )

        # Проверка запроса
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(response.data['items'][0]['quantity'], 2)
    
    def test_add_to_cart_products_and_over_update_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с неправильным товаром
        product_data_worng = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }

        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }
        
        # Неправильное добавление в корзину анонимно и проверка
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data_worng)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Добавление первого товара в корзину анонимно правильно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)

        # Получение item_id
        item_id = self.anon_client.get(reverse('cart:cart-list')).data['items'][0]['id']

        # Обновлнение на неправильное количество анонимно
        response = self.anon_client.patch(
            reverse('cart:cart-update-cart-item', kwargs={'item_id': item_id}), data={'quantity': 1000}
        )

        # Проверка запроса
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины анонимно после обновления
        response = self.anon_client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertNotEqual(response.data['items'][0]['quantity'], 1000)

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Получение item_id
        item_id = self.client.get(reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}).data['items'][0]['id']

        # Обновлнение на неправильное количество обычным пользователем
        response = self.client.patch(
            reverse('cart:cart-update-cart-item', kwargs={'item_id': item_id}), 
            data={'quantity': 1000}, headers={'Authorization': f'Bearer {self.access_token}'},
        )

        # Проверка запроса
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertNotEqual(response.data['items'][0]['quantity'], 1000)

    def test_add_to_cart_products_and_right_remove_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)

        # Получение item_id
        item_id = self.anon_client.get(reverse('cart:cart-list')).data['items'][0]['id']

        # Удаление из корзины анонимно
        response = self.anon_client.delete(
            reverse('cart:cart-remove-cart-item', kwargs={'item_id': item_id})
        )

        # Получение корзины анонимно после удаления
        response = self.anon_client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после удаления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение item_id
        item_id = response.data['items'][0]['id']

        # Удаление из корзины обычным пользователем
        response = self.client.delete(
            reverse('cart:cart-remove-cart-item', kwargs={'item_id': item_id}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

    def test_add_to_cart_products_and_wrong_remove_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)

        # Неправильное удаление из корзины анонимно
        response = self.anon_client.delete(
            reverse('cart:cart-remove-cart-item', kwargs={'item_id': 50})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение корзины анонимно после удаления
        response = self.anon_client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после удаления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(response.data['items'][0]['quantity'], product_data.get('quantity'))

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Неправильное удаление из корзины обычным пользователем
        response = self.client.delete(
            reverse('cart:cart-remove-cart-item', kwargs={'item_id': 50}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
        self.assertEqual(response.data['items'][0]['quantity'], product_data.get('quantity'))

    def test_clear_cart_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)

        # Очистка корзины анонимно
        response = self.anon_client.delete(reverse('cart:cart-clear-cart'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины анонимно после очистки
        response = self.anon_client.get(reverse('cart:cart-list'))
        
        # Проверка корзины анонимно после очистки
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:cart-add-to-cart'), data=product_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Очистка корзины обычным пользователем
        response = self.client.delete(
            reverse('cart:cart-clear-cart'), headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины обычным пользователем после очистки
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'}
        )

        # Проверка корзины обычным пользователем после очистки
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

    def test_merge_cart_by_anon_to_normal_user(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.anon_client.post(reverse('cart:cart-add-to-cart'), data=product_data)

        # Логин и мердж корзины обычным анонимом (теперь уже обычным пользователем)
        response = self.anon_client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        self.access_token = response.data.get('access')

        # Проверка старой корзины анонимно
        response = self.anon_client.get(reverse('cart:cart-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'], [])

        # Проверка новой корзины через другую сессиию обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['product_title'], self.product1.title)
