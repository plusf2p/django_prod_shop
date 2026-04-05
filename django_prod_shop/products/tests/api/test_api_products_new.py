from unittest.mock import patch

from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.products.models import Category, Product

user_model = get_user_model()


class ProductsAPITest(APITestCase):
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
    
    def get_product_list_url_with_kwargs(self, kwargs=None):
        return reverse('products:product-list', kwargs=kwargs)
    
    def get_product_detail_url_with_kwargs(self, kwargs=None):
        return reverse('products:product-detail', kwargs=kwargs)
    
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
    
    def test_get_products_search_list_by_anon_user(self):
        # Получение второго товара по поиску по полю title
        response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?search=second')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product2.title)
        self.assertNotContains(response, self.product1.title)

        # Получение первого товара по поиску по полю title
        response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?search=first')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product1.title)
        self.assertNotContains(response, self.product2.title)

    def test_get_products_filter_list_by_anon_user(self):
        # Получение второго товара по фильтру по полю price
        response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?price_min=300')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product1.title)
        self.assertNotContains(response, self.product2.title)

        # Получение второго товара по фильтру по полю slug
        response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?slug=test-title-of-second-product')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product2.title)
        self.assertNotContains(response, self.product1.title)

        # Получение обоих товаров по фильтру по полю title
        response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?title=test')
        
        # Проверка на совпадение обоих товаров
        self.assertContains(response, self.product2.title)
        self.assertContains(response, self.product1.title)
    
    def test_get_products_list_and_detail_products_by_anon_user(self):
        # Получение всех товаров
        list_response = self.anon_client.get(self.get_product_list_url_with_kwargs())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Проверка первого товара
        self.assertContains(list_response, self.product1.title)
        self.assertContains(list_response, self.product1.slug)
        self.assertContains(list_response, self.product1.price)

        # Проверка второго товара
        self.assertContains(list_response, self.product2.title)
        self.assertContains(list_response, self.product2.slug)
        self.assertContains(list_response, self.product2.price)

        # Взятие одного товара
        detail_response = self.anon_client.get(self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка одного товара
        self.assertContains(detail_response, self.product1.title)
        self.assertContains(detail_response, self.product1.slug)
        self.assertContains(detail_response, self.product1.price)

        # Неправильное взятие одного товара
        wrong_detail_response = self.anon_client.get(self.get_product_detail_url_with_kwargs(kwargs={'slug': 'wrong-slug'}))
        self.assertEqual(wrong_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_create_product_by_anon_and_normal_users(self):
        # Создание одного товара
        product_data = {
            'title': 'Test create title',
            'category_id': self.category.pk,
            'quantity': 100,
            'reserved_quantity': 50,
            'description': 'Test create description',
            'slug': 'test-create-title',
            'price': 199,
            'is_active': True,
        }

        # Неправильная попытка создать товар анонимно
        wrong_anon_response = self.anon_client.post(self.get_product_list_url_with_kwargs(), data=product_data)
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Неправильная попытка создать товар обычному пользователю
        wrong_normal_response = self.client.post(self.get_product_list_url_with_kwargs(), data=product_data)
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_right_create_product_and_get_it_by_admin_user(self):
        # Создание одного товара
        product_data = {
            'title': 'Test create title',
            'category_id': self.category.pk,
            'quantity': 100,
            'reserved_quantity': 50,
            'description': 'Test create description',
            'slug': 'test-create-title',
            'price': 199,
            'is_active': True,
        }

        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Создание товара админом и проверка
        new_created_product_response = self.admin_client.post(self.get_product_list_url_with_kwargs(), data=product_data)
        self.assertEqual(new_created_product_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного товара
        self.assertEqual(new_created_product_response.data['title'], product_data['title'])
        self.assertEqual(new_created_product_response.data['slug'], product_data['slug'])
        self.assertEqual(new_created_product_response.data['reserved_quantity'], product_data['reserved_quantity'])

        # Взятие нового товара и проверка
        new_product = get_object_or_404(Product, slug=product_data['slug'])
        new_product_response = self.client.get(self.get_product_detail_url_with_kwargs(kwargs={'slug': new_product.slug}))
        self.assertEqual(new_product_response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.assertContains(new_product_response, new_product.title)
        self.assertContains(new_product_response, new_product.slug)
        self.assertContains(new_product_response, new_product.price)

    def test_wrong_create_product_and_get_it_by_admin_user(self):
        # Неправильное создание одного товара
        wrong_product_data = {
            'title': 'Wrong title',
            'description': 'Wrong description',
            'slug': 'wrong-title',
        }
        
        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Неправильная попытка создать товар админом
        wrong_product_response = self.admin_client.post(self.get_product_list_url_with_kwargs(), data=wrong_product_data)
        self.assertEqual(wrong_product_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Взятие несуществующего товара после попытки создания и проверка
        wrog_product_detail_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': wrong_product_data.get('slug')})
        )
        self.assertEqual(wrog_product_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_product_by_anon_and_normal_users(self):
        # Полное обновление одного товара
        new_product_data = {
            'title': 'New test create title',
            'category_id': self.category.pk,
            'quantity': 99,
            'reserved_quantity': 0,
            'description': 'New test create description',
            'slug': 'test-create-title',
            'price': 199,
            'is_active': True,
        }

        # Неправильная попытка обновить товар анонимно
        wrong_anon_response = self.anon_client.put(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), data=new_product_data
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Неправильная попытка обновить товар обычному пользователю 
        wrong_normal_response = self.client.put(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), data=new_product_data,
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # 256 - test_api_products
