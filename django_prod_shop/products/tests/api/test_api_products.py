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
        serched_response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?search=second')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(serched_response, self.product2.title)
        self.assertNotContains(serched_response, self.product1.title)

        # Получение первого товара по поиску по полю title
        serched_response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?search=first')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(serched_response, self.product1.title)
        self.assertNotContains(serched_response, self.product2.title)

    def test_get_products_filter_list_by_anon_user(self):
        # Получение второго товара по фильтру по полю price
        filtered_response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?price_min=300')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(filtered_response, self.product1.title)
        self.assertNotContains(filtered_response, self.product2.title)

        # Получение второго товара по фильтру по полю slug
        filtered_response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?slug=test-title-of-second-product')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(filtered_response, self.product2.title)
        self.assertNotContains(filtered_response, self.product1.title)

        # Получение обоих товаров по фильтру по полю title
        filtered_response = self.anon_client.get(f'{self.get_product_list_url_with_kwargs()}?title=test')
        
        # Проверка на совпадение обоих товаров
        self.assertContains(filtered_response, self.product2.title)
        self.assertContains(filtered_response, self.product1.title)
    
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

        # Взятие товара
        detail_response = self.anon_client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug})
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка товара
        self.assertContains(detail_response, self.product1.title)
        self.assertContains(detail_response, self.product1.slug)
        self.assertContains(detail_response, self.product1.price)

        # Неправильное взятие товара
        wrong_detail_response = self.anon_client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': 'wrong-slug'})
        )
        self.assertEqual(wrong_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_create_product_by_anon_and_normal_users(self):
        # Данные для создания товара
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
        wrong_anon_response = self.anon_client.post(
            self.get_product_list_url_with_kwargs(), data=product_data
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

        # Неправильная попытка создать товар обычному пользователю
        wrong_normal_response = self.client.post(
            self.get_product_list_url_with_kwargs(), data=product_data
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_right_create_product_and_get_it_by_admin_user(self):
        # Данные для создания товара
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
        new_created_product_response = self.admin_client.post(
            self.get_product_list_url_with_kwargs(), data=product_data,
        )
        self.assertEqual(new_created_product_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного товара
        self.assertEqual(new_created_product_response.data['title'], product_data['title'])
        self.assertEqual(new_created_product_response.data['slug'], product_data['slug'])
        self.assertEqual(
            new_created_product_response.data['reserved_quantity'], product_data['reserved_quantity']
        )

        # Взятие нового товара и проверка
        new_product = get_object_or_404(Product, slug=product_data['slug'])
        new_product_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': new_product.slug})
        )
        self.assertEqual(new_product_response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.assertContains(new_product_response, new_product.title)
        self.assertContains(new_product_response, new_product.slug)
        self.assertContains(new_product_response, new_product.price)

    def test_wrong_create_product_and_get_it_by_admin_user(self):
        # Неправильные данные для создания товара
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
        wrong_response = self.admin_client.post(
            self.get_product_list_url_with_kwargs(), data=wrong_product_data,
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Взятие несуществующего товара после попытки создания и проверка
        wrog_product_detail_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': wrong_product_data.get('slug')})
        )
        self.assertEqual(wrog_product_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_product_by_anon_and_normal_users(self):
        # Данные для полного обновления товара
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
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), 
            data=new_product_data,
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
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), 
            data=new_product_data,
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    
    def test_right_put_product_by_admin_user(self):
        # Данные для полного обновления товара
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

        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Полное обновление товара админом и проверка
        put_response = self.admin_client.put(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), 
            data=new_product_data,
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        
        # Взятие нового товара и проверка
        product_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': new_product_data.get('slug')})
        )
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.assertEqual(product_response.data.get('title'), new_product_data.get('title'))
        self.assertEqual(product_response.data.get('slug'), new_product_data.get('slug'))
        self.assertEqual(
            product_response.data.get('reserved_quantity'), new_product_data.get('reserved_quantity')
        )

    def test_wrong_put_product_by_admin_user(self):
        # Неправильные данныне для полного обновления
        wrong_product_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Неправильное полное обновление товара админом и проверка
        wrong_response = self.admin_client.put(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product2.slug}), 
            data=wrong_product_data,
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие товара после неправильного полного обновления
        wrong_response = self.admin_client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': wrong_product_data.get('slug')}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_patch_product_by_anon_and_normal_users(self):
        # Получение существующего товара и проверка
        product_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug})
        )
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)
        
        # Подготовка к частичному обновлению товара
        category_pk = get_object_or_404(Category, title=product_response.data['category_name']).pk

        # Данные для частичного обновления товара
        new_product_data = {
            'title': product_response.data['title'],
            'category_id': category_pk,
            'qauntity': product_response.data['quantity'],
            'reserved_quantity': 5,
            'description': product_response.data['description'],
            'slug': product_response.data['slug'],
            'price': 15,
            'is_active': True,
        }

        # Неправильное частичное обновление товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.patch(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), 
            data=new_product_data,
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

        # Неправильное частичное обновление товара обычным пользователем и проверка
        wrong_normal_response = self.client.patch(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),  
            data=new_product_data,
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_right_patch_product_by_admin_user(self):
        # Получение существующего товара и проверка
        product_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),
        )
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)
        
        # Подготовка к частичному обновлению товара
        category_pk = get_object_or_404(Category, title=product_response.data['category_name']).pk

        # Данные для частичного обновления товара
        new_product_data = {
            'title': product_response.data['title'],
            'category_id': category_pk,
            'quantity': product_response.data['quantity'],
            'reserved_quantity': 5,
            'description': product_response.data['description'],
            'slug': product_response.data['slug'],
            'price': 15,
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

        # Частичное обновление товара админом и проверка
        patch_response = self.admin_client.patch(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),
            data=new_product_data,
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # Взятие нового товара и проверка
        response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': new_product_data['slug']}),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.assertEqual(response.data.get('title'), new_product_data['title'])
        self.assertEqual(response.data.get('slug'), new_product_data['slug'])
        self.assertEqual(
            response.data.get('reserved_quantity'), new_product_data['reserved_quantity']
        )


    def test_wrong_patch_product_by_admin_user(self):
        # Неправильные данные для частичного обновления
        wrong_product_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Неправильное частичное обновление товара и проверка
        wrong_patch_response = self.admin_client.patch(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}), 
            data=wrong_product_data,
        )
        self.assertEqual(wrong_patch_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие товара после частичного обновления и проверка
        wrong_response = self.admin_client.get(
            reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_by_anon_and_normal_user(self):
        # Неправильное удаление товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.delete(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),
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

        # Неправильное удаление товара обычным пользователем и проверка
        wrong_normal_response = self.client.delete(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_delete_product_by_admin_user(self):
        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Удаление товара админом
        delete_response = self.admin_client.delete(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на наличие товара после удаления
        deleted_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': self.product1.slug}),
        )
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_in_active_product_by_anon_and_normal_users(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(
            title='Test in active product', category=self.category, quantity=15, reserved_quantity=15, 
            description='3', slug='test-in-active-product', price=299, is_active=False,
        )

        # Неправильное получение неактивного товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': in_active_product.slug}),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_404_NOT_FOUND)

        # Логин обычного пользователя
        login_response = self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.client, access_token)

        # Неправильное получение неактивного товара обычным пользователем и проверка
        wrong_normal_response = self.client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': in_active_product.slug}),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_in_active_product_by_admin_user(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(
            title='Test in active product', category=self.category, quantity=15, reserved_quantity=15, 
            description='3', slug='test-in-active-product', price=299, is_active=False,
        )

        # Логин админа
        login_response = self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
        )

        # Получение access токена и добавление заголовка
        access_token = login_response.data['access']
        self.auth_header_client(self.admin_client, access_token)

        # Попытка взять неактивный товар
        in_active_response = self.admin_client.get(
            self.get_product_detail_url_with_kwargs(kwargs={'slug': in_active_product.slug}),
        )
        self.assertEqual(in_active_response.status_code, status.HTTP_200_OK)
