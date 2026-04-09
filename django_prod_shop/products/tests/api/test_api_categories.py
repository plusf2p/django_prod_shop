from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.products.models import Category


user_model = get_user_model()


class CategoriesAPITest(APITestCase):
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

        ### Categories ###

        # Две стартовые категории
        cls.category1 = Category.objects.create(
            title='Test title of first category', slug='test-title-of-first-category', description='1'
        )
        cls.category2 = Category.objects.create(
            title='Test title of second category', slug='test-title-of-second-category', description='2'
        )

    def setUp(self):
        self.admin_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
            client=self.client,
        )
        self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
            client=self.admin_client,
        )
    
    def get_category_list_url_with_kwargs(self, kwargs=None):
        return reverse('products:category-list', kwargs=kwargs)
    
    def get_category_detail_url_with_kwargs(self, kwargs=None):
        return reverse('products:category-detail', kwargs=kwargs)
    
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
    
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        return response

    def test_get_categories_search_list_by_anon_user(self):
        # Получение второй категории по поиску по полю title
        searched_response = self.client.get(f'{self.get_category_list_url_with_kwargs()}?search=second')
        
        # Проверка на совпадение и несовпадение категорий
        self.assertContains(searched_response, self.category2.title)
        self.assertNotContains(searched_response, self.category1.title)

        # Получение первой категории по поиску по полю title
        searched_response = self.client.get(f'{self.get_category_list_url_with_kwargs()}?search=first')
        
        # Проверка на совпадение и несовпадение категорий
        self.assertContains(searched_response, self.category1.title)
        self.assertNotContains(searched_response, self.category2.title)

    def test_get_list_and_detail_categories_by_anon_user(self):
        # Взятие всех категорий и проверка
        list_response = self.client.get(self.get_category_list_url_with_kwargs())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение первой категории
        self.assertContains(list_response, self.category1.title)
        self.assertContains(list_response, self.category1.slug)

        # Проверка на совпадение второй категории
        self.assertContains(list_response, self.category2.title)
        self.assertContains(list_response, self.category2.slug)

        # Взятие категории и проверка
        detail_response = self.client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        self.assertContains(detail_response, self.category1.title)
        self.assertContains(detail_response, self.category1.slug)

        # Неправильное взятие категории и проверка
        wrong_detail_response = self.client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': 'wrong-slug'}),
        )
        self.assertEqual(wrong_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_create_category_by_anon_and_normal_users(self):
        # Данные для создания категории
        category_data = {
            'title': 'Test create title',
            'description': 'Test create description',
            'slug': 'test-create-title',
        }

        # Попытка создать категорию анонимно и проверка
        wrong_anon_response = self.anon_client.post(
            self.get_category_list_url_with_kwargs(), data=category_data,
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Попытка создать категорию обычному пользователю
        wrong_normal_response = self.client.post(
            self.get_category_list_url_with_kwargs(), data=category_data,
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_right_create_category_and_get_it_by_admin_user(self):
        # Данные для создания категории
        category_data = {
            'title': 'Test create title',
            'description': 'Test create description',
            'slug': 'test-create-title',
        }

        # Создание категории админом и проверка
        response = self.admin_client.post(
            self.get_category_list_url_with_kwargs(), data=category_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверка созданной категории
        self.assertEqual(response.data['title'], category_data['title'])
        self.assertEqual(response.data['slug'], category_data['slug'])
        self.assertEqual(response.data['description'], category_data['description'])

        # Взятие этой категории и проверка
        new_category = get_object_or_404(Category, slug=category_data['slug'])
        new_created_category_response = self.admin_client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': new_category.slug}),
        )
        self.assertEqual(new_created_category_response.status_code, status.HTTP_200_OK)

        # Проверка этой категории
        self.assertContains(new_created_category_response, new_category.title)
        self.assertContains(new_created_category_response, new_category.slug)

    def test_wrong_create_category_and_get_it_by_admin_user(self):
        # Неправильные данные для создания категории
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное создание категории и проврека
        wrong_response = self.admin_client.post(
            self.get_category_list_url_with_kwargs(), data=wrong_category_data,
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие категории после создания и проверка
        wrong_response = self.admin_client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': wrong_category_data['slug']}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_category_by_anon_and_normal_users(self):
        # Данные для полного обновления категории
        new_category_data = {
            'title': 'New put test',
            'description': 'New put description',
            'slug': 'new-put-test',
        }

        # Неправильное польное обновлуние категории анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.put(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}), 
            data=new_category_data,
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильное обновлкние категории обычным пользователем и проверка
        wrong_normal_response = self.client.put(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_right_put_category_by_admin_user(self):
        # Данные для полного обновления категории
        new_category_data = {
            'title': 'New put test',
            'description': 'New put description',
            'slug': 'new-put-test',
        }

        # Полное обновление категории админом и проверка
        put_response = self.admin_client.put(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
            data=new_category_data,
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        # Взятие новой категории и проверка
        category_response = self.admin_client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': new_category_data['slug']}),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)

        # Проверка новой категории
        self.assertEqual(category_response.data['title'], new_category_data['title'])
        self.assertEqual(category_response.data['slug'], new_category_data['slug'])

    def test_wrong_put_category_by_admin_user(self):
        # Неправильные данные для полного обновления категории
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        wrong_response = self.admin_client.put(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category2.slug}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие объекта Category после полного обновления
        wrong_response = self.admin_client.get(
            reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_category_by_anon_and_normal_users(self):
        # Получение существующей категории и проверка
        categoty_response = self.anon_client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
        )
        self.assertEqual(categoty_response.status_code, status.HTTP_200_OK)
        
        # ЧДанные для частичного обновления категории
        new_category_data = {
            'title': categoty_response.data['title'],
            'description': 'New put description',
            'slug': categoty_response.data['slug'],
        }

        # Неправильное частичное обновление категории анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.patch(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}), 
            data=new_category_data,
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильное частичное обновление категории обычным пользователем и проверка
        wrong_normal_response = self.client.patch(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),  
            data=new_category_data,
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_right_patch_category_by_admin_user(self):
        # Получение существующей каиегории и проверка
        category_response = self.client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)
        
        # Данные для частичного обновления категории
        new_category_data = {
            'title': category_response.data['title'],
            'description': 'New put description',
            'slug': category_response.data['slug'],
        }

        # Частичное обновление категории админом и проверка
        patch_response = self.admin_client.patch(
            self.get_category_detail_url_with_kwargs({'slug': self.category1.slug}), 
            data=new_category_data,
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # Взятие новой категории и проверка
        category_response = self.admin_client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': new_category_data.get('slug')}),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)

        # Проверка новой категории
        self.assertEqual(category_response.data['title'], new_category_data['title'])
        self.assertEqual(category_response.data['slug'], new_category_data['slug'])
    
    def test_wrong_patch_category_by_admin_user(self):
        # Неправильные данные для частичного обновления категории
        wrong_category_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное частичное обновление категории и проврека
        wrong_response = self.admin_client.patch(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category2.slug}), 
            data=wrong_category_data,
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие категории после частичного обновления и проверка
        wrong_response = self.admin_client.get(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': wrong_category_data.get('slug')}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_category_by_anon_and_normal_users(self):
        # Неправильное удаление категории анонимным пользователем и проврка
        wrong_anon_response = self.anon_client.delete(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Неправильное удаление категории обычным пользователем и проврка
        wrong_normal_response = self.client.delete(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_category_by_admin_user(self):
        # Удалиение категории админом
        delete_response = self.admin_client.delete(
            self.get_category_detail_url_with_kwargs(kwargs={'slug': self.category1.slug}), 
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на наличие удаленной категории
        deleted_response = self.admin_client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)
