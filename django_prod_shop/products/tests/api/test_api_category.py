from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Category


class CategoryAPITest(APITestCase):
    def setUp(self):
        ### Users app ####

        # Регистрация обычного пользователя
        self.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password1': '12345678',
            'password2': '12345678',
        }
        self.client.post(reverse('users:register'), data=self.normal_user_data)

        # Регистрация админа
        self.admin_user_data = {
            'email': 'admin@mail.ru',
            'password1': 'adminadmin',
            'password2': 'adminadmin',
        }
        self.client.post(reverse('users:register'), data=self.admin_user_data)

        # Получение профилей для будущего обращения к ним
        self.normal_profile = Profile.objects.get(user__email=self.normal_user_data['email'])
        self.admin_profile = Profile.objects.get(user__email=self.admin_user_data['email'])

        # Назначение пользователя админ правами
        user_model = get_user_model()
        admin_user = user_model.objects.get(pk=self.admin_profile.pk)
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        ### Category ###

        # Две стартовые категории
        self.category1 = Category.objects.create(
            title='Test title of first category', slug='test-title-of-first-category', description='1'
        )
        self.category2 = Category.objects.create(
            title='Test title of second category', slug='test-title-of-second-category', description='2'
        )

    def test_get_list_and_partial_categories_by_anon_user(self):
        # Взятие всех категорий
        response = self.client.get(reverse('products:category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, self.category1.title)
        self.assertContains(response, self.category1.slug)

        self.assertContains(response, self.category2.title)
        self.assertContains(response, self.category2.slug)

        # Взятие одной категории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, self.category1.title)
        self.assertContains(response, self.category1.slug)

        # Неправильное взятие одной категории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': 'wrong-slug'}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_create_and_get_partial_category_by_anon_and_normal_users(self):
        # Создание одной категории
        category_data = {
            'title': 'Test create title',
            'description': 'Test create description',
            'slug': 'test-create-title',
        }

        # Попытка создать категорию анонимно
        response = self.client.post(reverse('products:category-list'), data=category_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка создать категорию обычному пользователю
        response = self.client.post(
            reverse('products:category-list'), data=category_data,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_create_and_get_partial_category_by_admin_user(self):
        # Создание одной категории
        category_data = {
            'title': 'Test create title',
            'description': 'Test create description',
            'slug': 'test-create-title',
        }

        # Логин админа
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка создать категорию админу
        response = self.client.post(
            reverse('products:category-list'), data=category_data,
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверка созданной категории
        self.assertEqual(response.data.get('title'), category_data.get('title'))
        self.assertEqual(response.data.get('slug'), category_data.get('slug'))
        self.assertEqual(response.data.get('description'), category_data.get('description'))

        # Взятие этой категории
        new_category = get_object_or_404(Category, slug=category_data.get('slug'))

        response = self.client.get(reverse('products:category-detail', kwargs={'slug': new_category.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка этой категории
        self.assertContains(response, new_category.title)
        self.assertContains(response, new_category.slug)

        # Неправильное создание одной категории
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.post(
            reverse('products:category-list'), data=wrong_category_data,
            headers={'Authorization': f'Bearer {access_token}'},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одной категории после создания
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_partial_category_by_anon_and_normal_users(self):
        # Полное обновление одной категории
        new_category_data = {
            'title': 'New put test',
            'description': 'New put description',
            'slug': 'new-put-test',
        }

        # Попытка польностью обновить категорию анонимному пользователю
        response = self.client.put(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), data=new_category_data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка обновить категорию обычному пользователю
        response = self.client.put(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), 
            data=new_category_data, headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_put_partial_category_by_admin_user(self):
        # Полное обновление одной категории
        new_category_data = {
            'title': 'New put test',
            'description': 'New put description',
            'slug': 'new-put-test',
        }

        # Логин админа
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка полностью обновить категорию админу
        response = self.client.put(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), 
            data=new_category_data, headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Взятие новой категории
        response = self.client.get(
            reverse('products:category-detail', kwargs={'slug': new_category_data.get('slug')})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка новой категории
        self.assertEqual(response.data.get('title'), new_category_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_category_data.get('slug'))

        # Неправильное полное обновление одной категории
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.put(
            reverse('products:category-detail', kwargs={'slug': self.category2.slug}), 
            data=wrong_category_data, headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Category после полного обновления
        response = self.client.get(
            reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_partial_category_by_anon_and_normal_users(self):
        # Получение существующей категории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Частичное обновление одной категории
        new_category_data = {
            'title': response.data.get('title'),
            'description': 'New put description',
            'slug': response.data.get('slug'),
        }

        # Попытка частично обновить категорию анонимному пользователю
        response = self.client.patch(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), data=new_category_data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка частично обновить категорию обычному пользователю
        response = self.client.patch(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}),  
            data=new_category_data, headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_partial_category_by_admin_user(self):
        # Получение существующей каиегории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Частичное обновление одной категории
        new_category_data = {
            'title': response.data.get('title'),
            'description': 'New put description',
            'slug': response.data.get('slug'),
        }

        # Логин админа
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка частично обновить категорию админу
        response = self.client.patch(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), 
            data=new_category_data, headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Взятие новой категории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': new_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка новой категории
        self.assertEqual(response.data.get('title'), new_category_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_category_data.get('slug'))
    
        # Неправильное частичное обновление одной категории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category2.slug}))
        wrong_category_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.patch(
            reverse('products:category-detail', kwargs={'slug': self.category2.slug}), 
            data=wrong_category_data, headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одной категории после частичного обновления
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_partial_category_by_anon_and_normal_user(self):
        # Удаление категории анонимным пользователем
        response = self.client.delete(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Логин обычного пользователя
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.normal_user_data.get('email'),
            'password': self.normal_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка удалить товар категорию пользователю
        response = self.client.delete(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), 
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_partial_category(self):
         # Логин админа
        response = self.client.post(reverse('users:token_access'), data={
            'email': self.admin_user_data.get('email'),
            'password': self.admin_user_data.get('password1'),
        })
        access_token = response.data.get('access')

        # Попытка удалить категорию админу
        response = self.client.delete(
            reverse('products:category-detail', kwargs={'slug': self.category1.slug}), 
            headers={'Authorization': f'Bearer {access_token}'},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на наличие стартовой удаленной категории
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
