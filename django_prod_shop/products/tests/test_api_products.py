from django.urls import reverse
from django.shortcuts import get_object_or_404

from rest_framework.test import APITestCase
from rest_framework import status

from django_prod_shop.products.models import Product, Category


class ProductAPITest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Test category', description='test description', slug='test-category')
        # Два стартовых объекта Product
        self.product1 = Product.objects.create(
            title='Test title of first product', category=self.category, quantity=10, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=400, sell_counter=50, is_active=True,
        )
        self.product2 = Product.objects.create(
            title='Test title of second product', category=self.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=200, sell_counter=0, is_active=True,
        )
    def test_get_list_and_partial_products(self):
        # Взятие всех объектов Product
        response = self.client.get(reverse('products:product-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, self.product1.title)
        self.assertContains(response, self.product1.slug)
        self.assertContains(response, self.product1.price)

        self.assertContains(response, self.product2.title)
        self.assertContains(response, self.product2.slug)
        self.assertContains(response, self.product2.price)

        # Взятие одного объекта Product
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, self.product1.title)
        self.assertContains(response, self.product1.slug)
        self.assertContains(response, self.product1.price)

        # Неправильное взятие одного объекта Product
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': 'wrong-slug'}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_create_and_get_partial_product(self):
        # Создание одного объекта Product
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
        response = self.client.post(reverse('products:product-list'), data=product_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного объекта
        self.assertEqual(response.data.get('title'), product_data.get('title'))
        self.assertEqual(response.data.get('slug'), product_data.get('slug'))
        self.assertEqual(response.data.get('reserved_quantity'), product_data.get('reserved_quantity'))

        # Взятие этого объекта Product и его повторная проверка
        new_product = get_object_or_404(Product, slug=product_data.get('slug'))

        response = self.client.get(reverse('products:product-detail', kwargs={'slug': new_product.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, new_product.title)
        self.assertContains(response, new_product.slug)
        self.assertContains(response, new_product.price)

        # Неправильное создание одного объекта Product
        wrong_product_data = {
            'title': 'Wrong title',
            'description': 'Wrong description',
            'slug': 'wrong-title',
        }
        response = self.client.post(reverse('products:product-list'), data=wrong_product_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Product после создания
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_partial_product(self):
        # Полное обновление одного объекта Product
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
        response = self.client.put(reverse('products:product-detail', kwargs={'slug': self.product1.slug}), data=new_product_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Взятие нового объекта
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': new_product_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового объекта
        self.assertEqual(response.data.get('title'), new_product_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_product_data.get('slug'))
        self.assertEqual(response.data.get('reserved_quantity'), new_product_data.get('reserved_quantity'))

        # Неправильное полное обновление одного объекта Product
        wrong_product_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.put(reverse('products:product-detail', kwargs={'slug': self.product2.slug}), data=wrong_product_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Product после полного обновления
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_partial_product(self):
        # Получение существующего объекта Product
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Частичное обновление одного объекта Product
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
        response = self.client.patch(reverse('products:product-detail', kwargs={'slug': self.product1.slug}), data=new_product_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Взятие нового объекта Product
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': new_product_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового объекта Product
        self.assertEqual(response.data.get('title'), new_product_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_product_data.get('slug'))
        self.assertEqual(response.data.get('reserved_quantity'), new_product_data.get('reserved_quantity'))
    
        # Неправильное частичное обновление одного объекта Product
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        wrong_product_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.patch(reverse('products:product-detail', kwargs={'slug': self.product1.slug}), data=wrong_product_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Category после частичного обновления
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': wrong_product_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_partial_product(self):
        # Удаление стартового объекта Product
        response = self.client.delete(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на наличие стартового удаленного объекта Product
        response = self.client.get(reverse('products:product-detail', kwargs={'slug': self.product1.slug}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
