from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from django_prod_shop.products.models import Product, Category


class CartAPITest(APITestCase):
    def setUp(self):
        ### Users ####

        # Регистрация пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        self.client.post(reverse('users:register'), data=self.normal_user_data)

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
        response = self.client.get(reverse('cart:cart-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_add_to_cart_right_products_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }
        
        # Добавление первого товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно
        response = self.client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertContains(response.data, product_data.get('quantity'))

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Провкерка корзины обычным пользователем
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertContains(response.data, product_data.get('quantity'))

    def test_add_to_cart_over_products_and_get_it_by_anon_and_normal_users(self):
        # Добавление неправильного количества товара в корзину
        product_data_over = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }
        
        # Добавление неправильного количества товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data_over)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины анонимно
        response = self.client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data_over.get('quantity'))

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Добавление неправильного количества товара в корзину
        product_data_over = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }

        # Добавление неправильного количества товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data_over, headers={'Authorization': f'Bearer {access_token}'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины обычным пользователем
        response = self.client.get(reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'})
        
        # Проверка корзины обычным пользователем
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data_over.get('quantity'))
    
    def test_add_to_cart_products_and_right_update_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data)

        # Получение корзины анонимно
        response = self.client.get(reverse('cart:cart-list'))

        # Обновлнение на правильное количество анонимно
        response = self.client.patch(
            reverse('cart:update_cart_item', kwargs={'item_id': self.product1.pk}), data={'quantity': 2}
        )

        # Получение корзины анонимно после обновления
        response = self.client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertContains(response.data, 2)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'),headers={'Authorization': f'Bearer {access_token}'}
        )

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )

        # Получение корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Обновлнение на правильное количество обычным пользователем
        response = self.client.patch(
            reverse('cart:update_cart_item', kwargs={'item_id': self.product1.pk}), 
            data={'quantity': 2}, headers={'Authorization': f'Bearer {access_token}'},
        )

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertContains(response.data, 2)
    
    def test_add_to_cart_products_and_over_update_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data)

        # Получение корзины анонимно
        response = self.client.get(reverse('cart:cart-list'))

        # Обновлнение на неправильное количество анонимно
        response = self.client.patch(
            reverse('cart:update_cart_item', kwargs={'item_id': self.product1.pk}), data={'quantity': 1000}
        )

        # Получение корзины анонимно после обновления
        response = self.client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertNotContains(response.data, 1000)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'),headers={'Authorization': f'Bearer {access_token}'}
        )

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )

        # Получение корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Обновлнение на неправильное количество обычным пользователем
        response = self.client.patch(
            reverse('cart:update_cart_item', kwargs={'item_id': self.product1.pk}), 
            data={'quantity': 1000}, headers={'Authorization': f'Bearer {access_token}'},
        )

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertNotContains(response.data, 1000)

    def test_add_to_cart_products_and_right_remove_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data)

        # Удаление из корзины анонимно
        response = self.client.delete(
            reverse('cart:remove_cart_item', kwargs={'item_id': self.product1.pk})
        )

        # Получение корзины анонимно после удаления
        response = self.client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после удаления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data.get('quantity'))

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'),headers={'Authorization': f'Bearer {access_token}'}
        )

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )

        # Удаление из корзины обычным пользователем
        response = self.client.delete(
            reverse('cart:remove_cart_item', kwargs={'item_id': self.product1.pk}), 
            headers={'Authorization': f'Bearer {access_token}'},
        )

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data.get('quantity'))

    def test_add_to_cart_products_and_wrong_remove_it_and_get_it_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data)

        # Неправильное удаление из корзины анонимно
        response = self.client.delete(
            reverse('cart:remove_cart_item', kwargs={'item_id': self.product2.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины анонимно после удаления
        response = self.client.get(reverse('cart:cart-list'))

        # Проверка корзины анонимно после удаления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data.get('quantity'))

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Получение пустой корзины обычным пользователем
        response = self.client.get(
            reverse('cart:cart-list'),headers={'Authorization': f'Bearer {access_token}'}
        )

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )

        # Неправильное удаление из корзины обычным пользователем
        response = self.client.delete(
            reverse('cart:remove_cart_item', kwargs={'item_id': self.product2.pk}), 
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data.get('quantity'))

    def test_clear_cart_by_anon_and_normal_users(self):
        # Создание запроса с товаром
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        # Добавление первого товара в корзину анонимно
        response = self.client.post(reverse('cart:add_cart_item'), data=product_data)

        # Очистка корзины анонимно
        response = self.client.delete(reverse('cart:clear_cart'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины анонимно после обновления
        response = self.client.get(reverse('cart:cart-list'))
        
        # Проверка корзины анонимно после очистки
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response.data, self.product1.title)
        self.assertNotContains(response.data, product_data.get('quantity'))

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Добавление первого товара в корзину обычным пользователем
        response = self.client.post(
            reverse('cart:add_cart_item'), data=product_data, headers={'Authorization': f'Bearer {access_token}'}
        )

        # Очистка корзины обычным пользователем
        response = self.client.delete(
            reverse('cart:clear_cart'), headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины обычным пользователем после обновления 
        response = self.client.get(
            reverse('cart:cart-list'), headers={'Authorization': f'Bearer {access_token}'}
        )

        # Проверка корзины обычным пользователем после обновления
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response.data, self.product1.title)
        self.assertContains(response.data, 2)