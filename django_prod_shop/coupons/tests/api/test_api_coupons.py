from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Product, Category
from django_prod_shop.coupons.models import Coupon

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

        # Заказ
        self.order_data = {
            'full_name': 'Ildar Bbb',
            'address': 'Gagarina 20',
            'city': 'Moscow',
            'phone': '+88005553535',
        }

        ### Coupons ###

        # Купон
        self.coupon = {
            'code': 'test1',
            'discount': '50',
            'valid_from': timezone.now().date(),
            'valid_to': (timezone.now()+ timedelta(days=1)).date(),
            'is_active': True,
        }

        # Второй купон
        self.second_coupon = {
            'code': 'test2',
            'discount': '20',
            'valid_from': timezone.now().date(),
            'valid_to': (timezone.now()+ timedelta(days=1)).date(),
            'is_active': True,
        }

        # Создание второго купона
        Coupon.objects.create(**self.second_coupon)
    
    def test_get_list_and_partial_by_normal_and_admin_users(self):
        # Неправильная попытка получить список купонов обычным пользователем
        response = self.client.get(reverse('coupons:coupons-list'), headers={'Authorization': f'Bearer {self.access_token}'},)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Неправильная попытка получить один купон обычным пользователем
        response = self.client.get(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Правильная попытка получить список купонов админом
        response = self.admin_client.get(reverse('coupons:coupons-list'), headers={'Authorization': f'Bearer {self.access_token_admin}'},)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Правильная попытка получить один купон админом
        response = self.admin_client.get(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_put_partial_coupo_and_get_it_by_normal_and_admin_user(self):
        # Новые данные для купона
        new_coupon_data = {
            'code': self.second_coupon.get('code'),
            'valid_from': timezone.now().date(),
            'valid_to': (timezone.now()+ timedelta(days=15)).date(),
            'discount': 35,
            'is_active': False,
        }

        # Неправильная попытка поностью обновить купон обычным пользователем и проверка
        response = self.client.put(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            data=new_coupon_data, headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Правильная попытка поностью обновить купон админом и проверка
        response = self.admin_client.put(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            data=new_coupon_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Правильная попытка получить поностью обновленный купон админом и проверка
        response = self.client.get(
            reverse('coupons:coupons-detail', kwargs={'code': new_coupon_data.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_active'], False)

    def test_patch_partial_coupo_and_get_it_by_normal_and_admin_user(self):
        # Новые данные для купона
        new_coupon_data = {
            'code': self.second_coupon.get('code'),
            'valid_from': self.second_coupon.get('valid_from'),
            'valid_to': self.second_coupon.get('valid_to'),
            'is_active': False,
        }

        # Неправильная попытка частично обновить купон обычным пользователем и проверка
        response = self.client.patch(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            data=new_coupon_data, headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Правильная попытка частично обновить купон админом и проверка
        response = self.client.patch(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            data=new_coupon_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Правильная попытка получить частично обновленный купон админом и проверка
        response = self.client.get(
            reverse('coupons:coupons-detail', kwargs={'code': new_coupon_data.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_active'], False)

    def test_delete_coupon_by_normal_and_admin_users(self):
        # Неправильная попытка удалить купон обычным пользователем и проверка
        response = self.client.delete(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Правильная попытка удалить купон админом и проверка
        response = self.client.delete(
            reverse('coupons:coupons-detail', kwargs={'code': self.second_coupon.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_wrong_create_coupon_by_normal_user(self):
        # Неправильная попытка создать купон обычным пользователем и проверка
        response = self.client.post(
            reverse('coupons:coupons-list'), data=self.coupon,
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_wrong_create_coupon_by_admin_user(self):
        # Неправильный купон
        wrong_coupon = {
            'code': 'test1',
            'valid_from': (timezone.now()+ timedelta(days=1)).date(),
            'valid_to': timezone.now().date(),
            'is_active': True,
        }

        # Неправильная попытка создать купон админом проверка
        response = self.admin_client.post(
            reverse('coupons:coupons-list'), data=wrong_coupon,
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_right_create_coupon_by_admin_user(self):
        # Правильная попытка создать купон админом и проверка
        response = self.admin_client.post(
            reverse('coupons:coupons-list'), data=self.coupon,
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], self.coupon.get('code'))

    def test_wrong_apply_coupon_by_normal_and_admin_users(self):
        # Отключенный купон
        in_active_coupon = {
            'code': 'is_active_coupon',
            'discount': '20',
            'valid_from': timezone.now().date(),
            'valid_to': (timezone.now()+ timedelta(days=1)).date(),
            'is_active': False,
        }

        # Создание второго купона
        Coupon.objects.create(**in_active_coupon)

        # Неправильная попытка применить купон обычныи пользователем и проверка
        response = self.client.get(
            reverse('cart:cart-apply-coupon', kwargs={'code': in_active_coupon.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильная попытка применить купон админом и проверка
        response = self.admin_client.get(
            reverse('cart:cart-apply-coupon', kwargs={'code': 123}),
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_right_apply_coupon_by_anon_user(self):
        # Правильная попытка применить купон анонимно и проверка
        response = self.anon_client.get(reverse('cart:cart-apply-coupon', kwargs={'code': self.second_coupon.get('code')}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['coupon'], self.second_coupon.get('code'))
    
    def test_create_order_with_coupon_by_normal_user(self):
        # Применение купона обычным пользователем
        response = self.client.get(
            reverse('cart:cart-apply-coupon', kwargs={'code': self.second_coupon.get('code')}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )

        # Cоздание заказа обычным пользователем и проверка
        response = self.client.post(
            reverse('orders:orders-list'), data=self.order_data, headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.data['coupon'], self.second_coupon.get('code'))
