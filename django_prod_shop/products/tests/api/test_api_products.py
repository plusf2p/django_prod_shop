from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Product, Category


class ProductAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.anon_client = APIClient()
        self.admin_client = APIClient()

        ### Users ####

        # Регистрация обычного пользователя
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

        # Регистрация админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password1': 'adminadmin',
            'password2': 'adminadmin',
        }
        self.admin_client.post(reverse('users:register'), data=self.admin_user_data)

        # Логин админа пользователя и проверка
        response = self.admin_client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })
        self.access_token_admin = response.data.get('access')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


        # Получение профилей для будущего обращения к ним
        self.normal_profile = Profile.objects.get(user__email=self.normal_user_data['email'])
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])

        # Назначение пользователя админ правами
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

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
    
    def test_get_search_list(self):
        # Получение второго товара по поиску по полю title
        response = self.client.get(f'{reverse('products:product-list')}?search=second')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product2.title)
        self.assertNotContains(response, self.product1.title)

        # Получение первого товара по поиску по полю title
        response = self.client.get(f'{reverse('products:product-list')}?search=first')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product1.title)
        self.assertNotContains(response, self.product2.title)
    
    def test_get_filter_list(self):
        # Получение второго товара по фильтру по полю price
        response = self.client.get(f'{reverse('products:product-list')}?price_min=300')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product1.title)
        self.assertNotContains(response, self.product2.title)

        # Получение второго товара по фильтру по полю slug
        response = self.client.get(f'{reverse('products:product-list')}?slug=test-title-of-second-product')
        
        # Проверка на совпадение и несовпадение товаров
        self.assertContains(response, self.product2.title)
        self.assertNotContains(response, self.product1.title)

        # Получение обоих товаров по фильтру по полю title
        response = self.client.get(f'{reverse('products:product-list')}?title=test')
        
        # Проверка на совпадение обоих товаров
        self.assertContains(response, self.product2.title)
        self.assertContains(response, self.product1.title)

    def test_get_list_and_partial_products_by_anon_user(self):
        # Получение всех товаров
        response = self.client.get(reverse('products:product-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка первого товара
        self.assertContains(response, self.product1.title)
        self.assertContains(response, self.product1.slug)
        self.assertContains(response, self.product1.price)

        # Проверка второго товара
        self.assertContains(response, self.product2.title)
        self.assertContains(response, self.product2.slug)
        self.assertContains(response, self.product2.price)

        # Взятие одного товара
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка одного товара
        self.assertContains(response, self.product1.title)
        self.assertContains(response, self.product1.slug)
        self.assertContains(response, self.product1.price)

        # Неправильное взятие одного товара
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': 'wrong-slug'}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_create_and_get_partial_product_by_anon_and_normal_users(self):
        # Создание одного товара
        product_data = {
            'title': 'Test create title',
            'category_id': self.category.pk,
            'qauntity': 100,
            'reserved_quantity': 50,
            'description': 'Test create description',
            'slug': 'test-create-title',
            'price': 199,
            'sell_counter': 0,
            'is_active': True,
        }

        # Попытка создать товар анонимно
        response = self.anon_client.post(reverse('products:product-list'), data=product_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Попытка создать товар обычному пользователю
        response = self.client.post(
            reverse('products:product-list'), data=product_data,
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_create_and_get_partial_product_by_admin_user(self):
        # Создание одного товара
        product_data = {
            'title': 'Test create title',
            'category_id': self.category.pk,
            'qauntity': 100,
            'reserved_quantity': 50,
            'description': 'Test create description',
            'slug': 'test-create-title',
            'price': 199,
            'sell_counter': 0,
            'is_active': True,
        }

        # Попытка создать товар админу
        response = self.admin_client.post(
            reverse('products:product-list'), data=product_data,
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного товара
        self.assertEqual(response.data.get('title'), product_data.get('title'))
        self.assertEqual(response.data.get('slug'), product_data.get('slug'))
        self.assertEqual(response.data.get('reserved_quantity'), product_data.get('reserved_quantity'))

        # Взятие этого нового товара
        new_product = get_object_or_404(Product, slug=product_data.get('slug'))
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': new_product.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка этого нового товара
        self.assertContains(response, new_product.title)
        self.assertContains(response, new_product.slug)
        self.assertContains(response, new_product.price)

        # Неправильное создание одного товара
        wrong_product_data = {
            'title': 'Wrong title',
            'description': 'Wrong description',
            'slug': 'wrong-title',
        }
        response = self.admin_client.post(
            reverse('products:product-list'), data=wrong_product_data,
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного товара после создания
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_partial_product_by_anon_and_normal_users(self):
        # Полное обновление одного товара
        new_product_data = {
            'title': 'New test create title',
            'category_id': self.category.pk,
            'qauntity': 99,
            'reserved_quantity': 0,
            'description': 'New test create description',
            'slug': 'test-create-title',
            'price': 199,
            'sell_counter': 0,
            'is_active': True,
        }

        # Попытка обновить товар анонимно
        response = self.anon_client.put(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), data=new_product_data
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Попытка обновить товар обычному пользователю
        response = self.client.put(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), 
            data=new_product_data, headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_partial_product_by_admin_user(self):
        # Полное обновление товара
        new_product_data = {
            'title': 'New test create title',
            'category_id': self.category.pk,
            'qauntity': 99,
            'reserved_quantity': 0,
            'description': 'New test create description',
            'slug': 'test-create-title',
            'price': 199,
            'sell_counter': 0,
            'is_active': True,
        }

        # Попытка полностью обновить товар админу
        response = self.admin_client.put(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), 
            data=new_product_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Взятие нового товара
        response = self.client.get(
            reverse('products:product-detail', kwargs={'slug': new_product_data.get('slug')})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.assertEqual(response.data.get('title'), new_product_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_product_data.get('slug'))
        self.assertEqual(response.data.get('reserved_quantity'), new_product_data.get('reserved_quantity'))

        # Неправильное полное обновление товара админом
        wrong_product_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.admin_client.put(
            reverse('products:product-detail', kwargs={'slug': self.product2.slug}), 
            data=wrong_product_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного товара после полного обновления
        response = self.admin_client.get(
            reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_partial_product_by_anon_and_normal_users(self):
        # Получение существующего товара
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Подготовка к частичному обновлению товара
        category_pk = get_object_or_404(Category, title=response.data['category_name']).pk
        new_product_data = {
            'title': response.data.get('title'),
            'category_id': category_pk,
            'qauntity': response.data.get('quantity'),
            'reserved_quantity': 5,
            'description': response.data.get('description'),
            'slug': response.data.get('slug'),
            'price': 15,
            'sell_counter': response.data.get('sell_counter'),
            'is_active': response.data.get('is_active'),
        }

        # Частичное обновление товара анонимным пользователем
        response = self.anon_client.patch(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), data=new_product_data
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Попытка частично обновить товар обычному пользователю
        response = self.client.patch(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}),  
            data=new_product_data, headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_patch_partial_product_by_admin_user(self):
        # Получение существующего товара
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Подготовка к частичному обновлению товара
        category_pk = get_object_or_404(Category, title=response.data['category_name']).pk
        new_product_data = {
            'title': response.data.get('title'),
            'category_id': category_pk,
            'qauntity': response.data.get('quantity'),
            'reserved_quantity': 5,
            'description': response.data.get('description'),
            'slug': response.data.get('slug'),
            'price': 15,
            'sell_counter': response.data.get('sell_counter'),
            'is_active': response.data.get('is_active'),
        }

        # Попытка частично обновить товар админу
        response = self.admin_client.patch(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), 
            data=new_product_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Взятие нового товара
        response = self.client.get(
            reverse('products:product-detail', kwargs={'slug': new_product_data.get('slug')})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.assertEqual(response.data.get('title'), new_product_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_product_data.get('slug'))
        self.assertEqual(response.data.get('reserved_quantity'), new_product_data.get('reserved_quantity'))
    
        # Неправильное частичное обновление одного товара
        response = self.admin_client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        wrong_product_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.admin_client.patch(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), 
            data=wrong_product_data, headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного товара после частичного обновления
        response = self.admin_client.get(
            reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_partial_product_by_anon_and_normal_user(self):
        # Удаление товара анонимным пользователем
        response = self.anon_client.delete(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Попытка удалить товар обычному пользователю
        response = self.client.delete(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), 
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_partial_product_by_admin_user(self):
        # Попытка удалить товар админу
        response = self.admin_client.delete(
            reverse('products:product-detail', kwargs={'slug': self.product1.slug}), 
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на наличие стартового удаленного товара
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_inactive_product_by_anon_and_normal_users(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(
            title='Test in active product', category=self.category, quantity=15, reserved_quantity=15, 
            description='3', slug='test-in-active-product', price=299, sell_counter=0, is_active=False,
        )

        # Получение неактивного товара анонимным пользователем
        response = self.anon_client.get(reverse('products:product-detail', kwargs={'slug': in_active_product.slug}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Получение неактивного товара обычным пользователем
        response = self.client.get(
            reverse('products:product-detail', kwargs={'slug': in_active_product.slug}),
            headers={'Authorization': f'Bearer {self.access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_inactive_product_by_admin_user(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(
            title='Test in active product', category=self.category, quantity=15, reserved_quantity=15, 
            description='3', slug='test-in-active-product', price=299, sell_counter=0, is_active=False,
        )

        # Попытка взять неактивный товар
        response = self.admin_client.get(
            reverse('products:product-detail', kwargs={'slug': in_active_product.slug}), 
            headers={'Authorization': f'Bearer {self.access_token_admin}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
