from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.coupons.models import Coupon
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
        cls.normal_user = user_model.objects.create_user(
            email=cls.normal_user_data['email'], 
            password=cls.normal_user_data['password'],
            is_active=True,
        )

        # Создание админа (суперюзера)
        cls.admin_user_data = {
            'email': 'admin@mail.ru',
            'password': 'admin_password!',
        }
        cls.admin_user = user_model.objects.create_superuser(
            email=cls.admin_user_data['email'], 
            password=cls.admin_user_data['password'],
            is_active=True,
        )

        # Объявление url
        cls.token_create_url = reverse('users:token-access')
        cls.cart_list_url = reverse('cart:cart-list')
        cls.add_to_cart_url = reverse('cart:cart-add-to-cart')
        cls.apply_coupon_cart_url = reverse('cart:cart-apply-coupon')
        cls.remove_coupon_cart_url = reverse('cart:cart-remove-coupon')
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
        cls.product_inactive = Product.objects.create(
            title='Test title of inactive product', category=cls.category, quantity=100, reserved_quantity=10, 
            description='inative', slug='test-title-of-inactive-product', price=200, is_active=False,
        )

        ### Coupons ###

        # Данные для создания купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Создание трёх купонов
        cls.coupon1 = Coupon.objects.create(
            code='test-coupon-123321',
            valid_from=time_start,
            valid_to=time_end,
            discount=50,
            is_active=True
        )
        cls.coupon2 = Coupon.objects.create(
            code='test-coupon-321123',
            valid_from=time_start,
            valid_to=time_end,
            discount=25,
            is_active=True
        )
        cls.coupon_inactive = Coupon.objects.create(
            code='test-coupon-inactive',
            valid_from=time_start,
            valid_to=time_end,
            discount=50,
            is_active=False
        )

    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.normal_client.force_authenticate(user=self.normal_user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def get_cart_update_url_with_kwargs(self, item_id):
        return reverse('cart:cart-update-cart-item', kwargs={'item_id': item_id})
    
    def get_cart_remove_url_with_kwargs(self, item_id):
        return reverse('cart:cart-remove-cart-item', kwargs={'item_id': item_id})
    
    def add_to_cart_test_product(self, client=None):
        # Добавление тестового товара в корзину
        if client is None:
            client = self.normal_client

        test_product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }

        test_response = client.post(
            self.add_to_cart_url, data=test_product_data, format='json',
        )
        self.assertEqual(test_response.status_code, status.HTTP_200_OK)
    
    def apply_coupon(self, client, code, expected_stats=status.HTTP_200_OK):
        test_response = client.post(
            self.apply_coupon_cart_url, data={'code': code}, format='json',
        )
        self.assertEqual(test_response.status_code, expected_stats)

        return test_response

    def get_cart(self, client=None):
        # Получение корзины
        if client is None:
            client = self.normal_client
        
        cart_response = client.get(self.cart_list_url)
        self.assertEqual(cart_response.status_code, status.HTTP_200_OK)

        return cart_response

    def get_cart_item_id(self, cart, product_slug):
        for item in cart.data['items']:
            if item['product_slug'] == product_slug:
                return item['id']
        self.fail(f"Товар со слагом '{product_slug}' не найден в корзине")

    def check_in_cart_product_with_quantity(self, cart, product_slug, expected_quantity):
        for item in cart.data['items']:
            if item['product_slug'] == product_slug:
                self.assertEqual(item['quantity'], expected_quantity)
                return
        self.fail(f"Количество у товаара со слагом'{product_slug}' не совпадает")

    def check_empty_cart(self, cart_response):
        self.assertEqual(cart_response.data['items'], [])
        self.assertEqual(cart_response.data['total_quantity'], 0)

    def check_cart_totals(self, cart_response, expected_total_quantity, expected_total_price):
        self.assertEqual(cart_response.data['total_quantity'], expected_total_quantity)
        self.assertEqual(str(cart_response.data['total_price']), expected_total_price)

    def test_get_empty_cart_by_anon_user(self):
        # Получение пустой корзины анонимно и проверка
        cart_anon_response = self.get_cart(self.anon_client)
        self.check_empty_cart(cart_anon_response)

    def test_get_empty_cart_by_normal_user(self):
        # Получение пустой корзины обычным пользователем и проверка
        cart_normal_response = self.get_cart()
        self.check_empty_cart(cart_normal_response)
    
    def test_anon_user_can_add_to_cart_products_twice(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Добавление товара в корзину анонимно снова
        self.add_to_cart_test_product(client=self.anon_client)

        # Получение корзины и проверка количества после двух одиночных добавлений
        cart_anon_response = self.get_cart(client=self.anon_client)
        self.check_in_cart_product_with_quantity(
            cart=cart_anon_response, 
            product_slug=self.product1.slug,
            expected_quantity=2
        )
        self.check_cart_totals(
            cart_anon_response, 
            expected_total_quantity=2, 
            expected_total_price='800.00',
        )

    def test_anon_user_can_add_to_cart_two_products(self):
        # Данные товаров для добавления в корзину
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }
        product_data_2 = {
            'product_slug': self.product2.slug,
            'quantity': 1,
        }
        
        # Добавление товаров в корзину анонимно и проверка
        add_to_cart_anon_response = self.anon_client.post(
            self.add_to_cart_url, data=product_data, format='json',
        )
        self.assertEqual(add_to_cart_anon_response.status_code, status.HTTP_200_OK)
        add_to_cart_anon_response = self.anon_client.post(
            self.add_to_cart_url, data=product_data_2, format='json',
        )
        self.assertEqual(add_to_cart_anon_response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно
        cart_anon_response = self.get_cart(self.anon_client)

        # Проверка корзины анонимно
        self.check_in_cart_product_with_quantity(
            cart=cart_anon_response, 
            product_slug=product_data['product_slug'],
            expected_quantity=product_data['quantity'],
        )
        self.check_in_cart_product_with_quantity(
            cart=cart_anon_response, 
            product_slug=product_data_2['product_slug'],
            expected_quantity=product_data_2['quantity'],
        )
        self.check_cart_totals(
            cart_anon_response,
              expected_total_quantity=2, 
            expected_total_price='600.00',
        )
        
    def test_normal_user_can_add_to_cart_two_products(self):
        # Данные товаров для добавления в корзину
        product_data = {
            'product_slug': self.product1.slug,
            'quantity': 1,
        }
        product_data_2 = {
            'product_slug': self.product2.slug,
            'quantity': 1,
        }

        # Добавление товаров в корзину обычным пользователем и проверка
        add_to_cart_normal_response = self.normal_client.post(
            self.add_to_cart_url, data=product_data, format='json',
        )
        self.assertEqual(add_to_cart_normal_response.status_code, status.HTTP_200_OK)
        add_to_cart_normal_response = self.normal_client.post(
            self.add_to_cart_url, data=product_data_2, format='json',
        )
        self.assertEqual(add_to_cart_normal_response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем
        cart_normal_response = self.get_cart()

        # Провкерка корзины обычным пользователем
        self.check_in_cart_product_with_quantity(
            cart=cart_normal_response, 
            product_slug=product_data['product_slug'],
            expected_quantity=product_data['quantity'],
        )
        self.check_in_cart_product_with_quantity(
            cart=cart_normal_response, 
            product_slug=product_data_2['product_slug'],
            expected_quantity=product_data_2['quantity'],
        )
        self.check_cart_totals(
            cart_normal_response, 
            expected_total_quantity=2, 
            expected_total_price='600.00',
        )

    def test_admin_user_cannot_add_to_cart_over_products(self):
        # Неправильные данные для добавления товара в корзину
        product_data_over = {
            'product_slug': self.product1.slug,
            'quantity': 10000,
        }

        # Добавление неправильного количества товара в корзину админом и проверка
        wrong_admin_response = self.admin_client.post(
            self.add_to_cart_url, data=product_data_over, format='json',
        )
        self.assertEqual(wrong_admin_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины админом
        cart_admin_response = self.get_cart(self.admin_client)
        
        # Проверка корзины админом
        self.check_empty_cart(cart_admin_response)
    
    def test_admin_user_cannot_add_to_cart_inactive_product(self):
        # Неактивные данные для добавления товара в корзину
        product_data_inactive = {
            'product_slug': self.product_inactive.slug,
            'quantity': 1,
        }

        # Добавление несуществующего товара в корзину админом и проверка
        wrong_admin_response = self.admin_client.post(
            self.add_to_cart_url, data=product_data_inactive, format='json',
        )
        self.assertEqual(wrong_admin_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины админом
        cart_admin_response = self.get_cart(self.admin_client)
        
        # Проверка корзины админом
        self.check_empty_cart(cart_admin_response)

    def test_admin_user_cannot_add_to_cart_products_with_invalid_data(self):
        # Неправильные данные для добавления товара в корзину
        product_data_over = {
            'product_slug': 'test-invalid-product',
            'quantity': 15,
        }

        # Добавление несуществующего товара в корзину админом и проверка
        wrong_admin_response = self.admin_client.post(
            self.add_to_cart_url, data=product_data_over, format='json',
        )
        self.assertEqual(wrong_admin_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины админом
        cart_admin_response = self.get_cart(self.admin_client)
        
        # Проверка корзины админом
        self.check_empty_cart(cart_admin_response)

    def test_admin_user_cannot_add_to_cart_product_with_0_quantity(self):
        # Неправильные данные для добавления товара в корзину
        product_data_invalid = {
            'product_slug': self.product1.slug,
            'quantity': 0,
        }

        # Добавление неправльного товара в корзину админом и проверка
        wrong_admin_response = self.admin_client.post(
            self.add_to_cart_url, data=product_data_invalid, format='json',
        )
        self.assertEqual(wrong_admin_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Получение корзины админом
        cart_admin_response = self.get_cart(self.admin_client)
        
        # Проверка корзины админом
        self.check_empty_cart(cart_admin_response)
    
    def test_anon_user_can_update_product_in_cart_to_0_and_product_deleted(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)
        
        # Получение item_id
        item_id = self.get_cart_item_id(
            cart=self.get_cart(self.anon_client), product_slug=self.product1.slug,
        )

        # Обновлнение количества на 0 анонимно и проверка
        cart_update_anon_response = self.anon_client.patch(
           self.get_cart_update_url_with_kwargs(item_id=item_id), 
           data={'quantity': 0}, format='json',
        )
        self.assertEqual(cart_update_anon_response.status_code, status.HTTP_200_OK)
    
        # Получение корзины анонимно после обновления
        cart_anon_response = self.get_cart(self.anon_client)

        # Проверка корзины анонимно после обновления
        self.check_empty_cart(cart_anon_response)

    def test_anon_user_can_add_to_cart_product_and_apply_coupon(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Применение купона анонимно и проверка
        coupon_anon_response = self.apply_coupon(
            client=self.anon_client, code=self.coupon1.code
        )
        self.assertEqual(coupon_anon_response.data['coupon'], self.coupon1.code)
        self.assertEqual(coupon_anon_response.data['discount'], self.coupon1.discount)
        self.assertEqual(str(coupon_anon_response.data['total_price']), '300.00')
    
    def test_anon_user_can_add_to_cart_product_and_twice_apply_coupon(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Применение купона анонимно и проверка
        coupon_anon_response = self.apply_coupon(
            client=self.anon_client, code=self.coupon1.code
        )
        self.assertEqual(coupon_anon_response.data['coupon'], self.coupon1.code)
        self.assertEqual(coupon_anon_response.data['discount'], self.coupon1.discount)
        self.assertEqual(str(coupon_anon_response.data['total_price']), '300.00')

        # Применение купона анонимно второй раз и проверка
        coupon_anon_response = self.apply_coupon(
            client=self.anon_client, code=self.coupon2.code
        )
        self.assertEqual(coupon_anon_response.data['coupon'], self.coupon2.code)
        self.assertEqual(coupon_anon_response.data['discount'], self.coupon2.discount)
        self.assertEqual(str(coupon_anon_response.data['total_price']), '450.00')

    def test_anon_user_can_add_to_cart_product_and_apply_coupon_and_remove_coupon(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Применение купона анонимно и проверка
        coupon_anon_response = self.apply_coupon(
            client=self.anon_client, code=self.coupon1.code
        )
        self.assertEqual(coupon_anon_response.data['coupon'], self.coupon1.code)
        self.assertEqual(coupon_anon_response.data['discount'], self.coupon1.discount)
        self.assertEqual(str(coupon_anon_response.data['total_price']), '300.00')

        # Удаление купона анонимно и проверка
        anon_coupon_response = self.anon_client.delete(self.remove_coupon_cart_url)
        self.assertEqual(anon_coupon_response.status_code, status.HTTP_200_OK)

        # Получение корзины и проверка купона
        cart_anon_response = self.get_cart(client=self.anon_client)
        self.assertIsNone(cart_anon_response.data['coupon'])
        self.assertEqual(str(cart_anon_response.data['total_price']), '600.00')

    def test_anon_user_cannot_add_to_cart_product_and_apply_inactive_coupon(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Применение неактивного купона анонимно и проверка
        self.apply_coupon(
            client=self.anon_client, 
            code=self.coupon_inactive.code,
            expected_stats=status.HTTP_400_BAD_REQUEST,
        )
        
        # Получение корзины анонимно и проверка
        cart_response = self.get_cart(self.anon_client)
        self.assertIsNone(cart_response.data['coupon'])
        self.assertEqual(str(cart_response.data['total_price']), '600.00')
    
    def test_anon_user_cannot_add_to_cart_product_and_apply_invalid_coupon(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Применение несуществующего купона анонимно и проверка
        self.apply_coupon(
            client=self.anon_client, 
            code='invalid-coupon',
            expected_stats=status.HTTP_400_BAD_REQUEST,
        )
        
        # Получение корзины анонимно и проверка
        cart_response = self.get_cart(self.anon_client)
        self.assertIsNone(cart_response.data['coupon'])
        self.assertEqual(str(cart_response.data['total_price']), '600.00')

    def test_normal_user_can_update_product_in_cart(self):
        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()
        
        # Получение item_id
        item_id = self.get_cart_item_id(
            cart=self.get_cart(), product_slug=self.product1.slug,
        )

        # Обновлнение на правильное количество обычным пользователем и проверка
        cart_update_normal_response = self.normal_client.patch(
           self.get_cart_update_url_with_kwargs(item_id=item_id), 
           data={'quantity': 2}, format='json',
        )
        self.assertEqual(cart_update_normal_response.status_code, status.HTTP_200_OK)
    
        # Получение корзины обычным пользователем после обновления
        cart_normal_response = self.get_cart()

        # Проверка корзины обычным пользователем после обновления
        self.check_in_cart_product_with_quantity(
            cart=cart_normal_response, 
            product_slug=self.product1.slug,
            expected_quantity=2,
        )

    def test_anon_user_can_remove_product_in_cart(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Получение item_id
        item_id = self.get_cart_item_id(
            cart=self.get_cart(self.anon_client), product_slug=self.product1.slug,
        )

        # Удаление из корзины анонимно и проверка
        delete_anon_response = self.anon_client.delete(
            self.get_cart_remove_url_with_kwargs(item_id=item_id),
        )
        self.assertEqual(delete_anon_response.status_code, status.HTTP_200_OK)

        # Получение корзины анонимно после удаления
        deleted_anon_response = self.get_cart(self.anon_client)

        # Проверка корзины анонимно после удаления
        self.assertEqual(deleted_anon_response.data['items'], [])

    def test_normal_user_can_remove_product_in_cart(self):
        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()

        # Получение item_id
        item_id = self.get_cart_item_id(
            cart=self.get_cart(), product_slug=self.product1.slug,
        )

        # Удаление из корзины обычным пользователем и проверка
        delete_normal_response = self.normal_client.delete(
            self.get_cart_remove_url_with_kwargs(item_id=item_id),
        )
        self.assertEqual(delete_normal_response.status_code, status.HTTP_200_OK)

        # Получение корзины обычным пользователем после удаления
        deleted_normal_response = self.get_cart()

        # Проверка корзины обычным пользователем после удаления
        self.assertEqual(deleted_normal_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted_normal_response.data['items'], [])

    def test_anon_user_cannot_remove_product_in_cart_with_invalid_data(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Неправильное удаление из корзины анонимно и проверка
        wrong_anon_response = self.anon_client.delete(
            self.get_cart_remove_url_with_kwargs(item_id=50000),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение корзины анонимно после удаления
        cart_anon_response = self.get_cart(self.anon_client)

        # Проверка корзины анонимно после удаления
        self.check_in_cart_product_with_quantity(
            cart=cart_anon_response, 
            product_slug=self.product1.slug,
            expected_quantity=1,
        )
        
    def test_normal_user_cannot_remove_product_in_cart_with_invalid_data(self):
        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()

        # Неправильное удаление из корзины обычным пользователем и проверка
        wrong_normal_response = self.normal_client.delete(
            self.get_cart_remove_url_with_kwargs(item_id=50),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение корзины обычным пользователем после удаления
        cart_normal_response = self.get_cart()

        # Проверка корзины обычным пользователем после удаления
        self.check_in_cart_product_with_quantity(
            cart=cart_normal_response, 
            product_slug=self.product1.slug,
            expected_quantity=1,
        )

    def test_anon_user_can_clear_cart(self):
        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Очистка корзины анонимно
        cart_clear_anon_response = self.anon_client.delete(self.clear_cart_url)
        self.assertEqual(cart_clear_anon_response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины анонимно после очистки
        cart_anon_response = self.get_cart(self.anon_client)
        
        # Проверка корзины анонимно после очистки
        self.check_empty_cart(cart_anon_response)

    def test_normal_user_can_clear_cart(self):
        # Добавление товара в корзину обычным пользователем
        self.add_to_cart_test_product()

        # Очистка корзины обычным пользователем
        cart_clear_normal_response = self.normal_client.delete(self.clear_cart_url)
        self.assertEqual(cart_clear_normal_response.status_code, status.HTTP_204_NO_CONTENT)

        # Получение корзины обычным пользователем после очистки
        cart_normal_response = self.get_cart()

        # Проверка корзины обычным пользователем после очистки
        self.check_empty_cart(cart_normal_response)
        
    def test_merge_cart_by_anon_to_normal_user(self):
        # Создание нового юзера для проверки слияния корзин
        user_model.objects.create_user(
            email='new_user123@mail.ru',
            password='new_user123@mail.ru',
            is_active=True,
        )

        # Добавление товара в корзину анонимно
        self.add_to_cart_test_product(client=self.anon_client)

        # Логин пользователя
        login_response = self.anon_client.post(
            self.token_create_url,
            data={
                'email': 'new_user123@mail.ru',
                'password': 'new_user123@mail.ru',
            },
            format='json',
        )

        # Проверка логина
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)

        # Получние access токена
        access_token = login_response.data['access']

        # Получение и проверка старой корзины анонимно
        cart_anon_response = self.get_cart(self.anon_client)
        self.check_empty_cart(cart_anon_response)

        # Привязка токена
        self.anon_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Проверка новой корзины через другую сессиию обычным пользователем
        cart_normal_response = self.get_cart(self.anon_client)
        self.check_in_cart_product_with_quantity(
            cart=cart_normal_response, product_slug=self.product1.slug, expected_quantity=1,
        )
