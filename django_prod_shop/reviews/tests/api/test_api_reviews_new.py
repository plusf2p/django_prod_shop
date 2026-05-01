from decimal import Decimal
from uuid import uuid4

from django.core.cache import cache
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.orders.models import Order, OrderItem, StatusChoices
from django_prod_shop.products.models import Category, Product
from django_prod_shop.reviews.models import Review


user_model = get_user_model()


class ReviewAPITest(APITestCase):
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

        ### Products ###

        # Создание стартовой категории
        cls.category = Category.objects.create(
            title='Test category', description='test description', slug='test-category'
        )
        
        # Создание двух стартовых товаров
        cls.product1 = Product.objects.create(
            title='Test title of first product', category=cls.category, quantity=10, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=800, is_active=True,
        )
        cls.product2 = Product.objects.create(
            title='Test title of second product', category=cls.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=400, is_active=True,
        )
        cls.product3 = Product.objects.create(
            title='Test title of third product', category=cls.category, quantity=99, reserved_quantity=9, 
            description='3', slug='test-title-of-third-product', price=200, is_active=True,
        )

        # Объявление url
        cls.reviews_list_url = reverse('reviews:reviews-list')
        cls.product1_detail_url = reverse('products:product-detail', kwargs={'slug': cls.product1.slug})

        ### Orders ###

        # Создание заказов
        cls.order_normal = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            total_price=Decimal('1.00'),
            status=StatusChoices.DELIVERED,
            yookassa_id=str(uuid4()),
        )

        cls.order_normal_without_reivews = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            total_price=Decimal('1.00'),
            status=StatusChoices.DELIVERED,
            yookassa_id=str(uuid4()),
        )

        cls.order_admin = Order.objects.create(
            order_id=uuid4(),
            user=cls.admin_user,
            full_name='Test full name admin',
            phone='+79999999999',
            address='Test address admin',
            city='Test city admin',
            total_price=Decimal('1.00'),
            status=StatusChoices.DELIVERED,
            yookassa_id=str(uuid4()),
        )

        # Создание элементов заказов
        OrderItem.objects.create(
            order=cls.order_normal,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=cls.order_normal_without_reivews,
            product=cls.product3,
            price=cls.product3.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=cls.order_admin,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )

        # Переопределение цен
        cls.order_normal.total_price = cls.order_normal.total_price_after_discount
        cls.order_normal.save(update_fields=['total_price'])

        cls.order_normal_without_reivews.total_price = cls.order_normal_without_reivews.total_price_after_discount
        cls.order_normal_without_reivews.save(update_fields=['total_price'])

        cls.order_admin.total_price = cls.order_admin.total_price_after_discount
        cls.order_admin.save(update_fields=['total_price'])

        ### Reviews ###

        # Создание отзывов
        cls.product1_normal_review = Review.objects.create(
            product=cls.product1,
            user=cls.normal_user,
            comment='product 1 review comment normal',
            rating=5,
        )
        cls.product1_admin_review = Review.objects.create(
            product=cls.product1,
            user=cls.admin_user,
            comment='product 1 review comment admin',
            rating=1,
        )

    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа, и двух обычных пользователей
        self.normal_client.force_authenticate(user=self.normal_user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def get_review_detail_with_pk(self, pk):
        return reverse('reviews:reviews-detail', kwargs={'id': pk})

    def check_review_in_review_data(self, review_data, review):
        self.assertEqual(review_data['comment'], review.comment)
        self.assertEqual(review_data['rating'], review.rating)
        self.assertEqual(review_data['user_id'], review.user.pk)

    def check_contains_review_in_product_response(self, product_response, review):
        for review_item in product_response.data['reviews']:
            if review.pk == review_item['id']:
                self.check_review_in_review_data(review_data=review_item, review=review)
                return
        self.fail(f"Отзыв с ID '{review_item.pk}' не найден в ответе")

    def test_anon_user_can_get_reviews_list_in_product(self):
        # Получение всех отзывов у товара и проверка
        product_response = self.anon_client.get(self.product1_detail_url)
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие отзывов в товаре
        self.check_contains_review_in_product_response(
            product_response=product_response, review=self.product1_normal_review,
        )
        self.check_contains_review_in_product_response(
            product_response=product_response,  review=self.product1_admin_review, 
        )
    
    def test_assert_rating_values_in_proudct(self):
        # Получение всех отзывов у товара и проверка
        product_response = self.anon_client.get(self.product1_detail_url)
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)

        # Расчет рейтинга и сравнение его с существующим
        avg_rating = round((self.product1_normal_review.rating + self.product1_admin_review) / 2, 1)
        self.assertEqual(product_response.data['rating'], avg_rating)
        self.assertEqual(product_response.data['rating_count'], 2)
    
    def test_anon_user_can_get_review_detail(self):
        # Получение детального отзыва и проверка
        detail_anon_response = self.anon_client.get(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk)
        )
        self.assertEqual(detail_anon_response.status_code, status.HTTP_200_OK)

        # Проверка на соответствие отзыва
        self.check_review_in_review_data(
            review_data=detail_anon_response.data, review=self.product1_normal_review, 
        )
    
    def test_anon_user_cannot_create_review(self):
        # Данные для отзыва
        review_data = {
            'product': self.product1.slug,
            'comment': 'test review comment',
            'rating': 1,
        }

        # Неправильное создание отзыва и проверка
        invalid_anon_response = self.anon_client.post(
            self.reviews_list_url, data=review_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_user_cannot_create_review_with_not_exists_product(self):
        # Неверные данные для отзыва
        invalid_review_data = {
            'product': 'not-exists-product',
            'comment': 'test review comment',
            'rating': 1,
        }

        # Неправильное создание отзыва и проверка
        invalid_admin_response = self.admin_client.post(
            self.reviews_list_url, data=invalid_review_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_user_cannot_create_review_without_rating(self):
        # Неверные данные для отзыва
        invalid_review_data = {
            'product': self.product3.slug,
            'comment': 'test review comment',
        }

        # Неправильное создание отзыва и проверка
        invalid_admin_response = self.admin_client.post(
            self.reviews_list_url, data=invalid_review_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_user_cannot_create_review_with_rating_gt_5(self):
        # Неверные данные для отзыва
        invalid_review_data = {
            'product': self.product3.slug,
            'comment': 'test review comment',
            'rating': 6,
        }

        # Неправильное создание отзыва и проверка
        invalid_admin_response = self.admin_client.post(
            self.reviews_list_url, data=invalid_review_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_admin_response.data['rating'][0], 'Рейтинг не может быть больше 5')
    
    def test_admin_user_cannot_create_review_with_rating_lt_1(self):
        # Неверные данные для отзыва
        invalid_review_data = {
            'product': self.product3.slug,
            'comment': 'test review comment',
            'rating': 0,
        }

        # Неправильное создание отзыва и проверка
        invalid_admin_response = self.admin_client.post(
            self.reviews_list_url, data=invalid_review_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_admin_response.data['rating'][0], 'Рейтинг не может быть меньше 1')
    
    def test_admin_user_cannot_create_review_if_his_own_review_for_this_product_already_exists(self):
        # Данные для отзыва
        review_data = {
            'product': self.product1.slug,
            'comment': 'test review comment',
            'rating': 4,
        }

        # Неправильное создание отзыва и проверка
        invalid_admin_response = self.admin_client.post(
            self.reviews_list_url, data=review_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_admin_response.data['product'][0], 'Вы уже оставляли отзыв на этот товаром')

    def test_normal_user_cannot_create_review_if_product_is_not_delivered(self):
        # Создание недоставленного заказа
        not_delivered_order = Order.objects.create(
            order_id=uuid4(),
            user=self.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            total_price=Decimal('1.00'),
            status=StatusChoices.PENDING,
            yookassa_id=str(uuid4()),
        )

        # Создание единицы заказа
        OrderItem.objects.create(
            order=not_delivered_order,
            product=self.product2,
            price=self.product2.price,
            quantity=1,
        )
        
        # Перерасчет цены заказа
        not_delivered_order.total_price = not_delivered_order.total_price_after_discount
        not_delivered_order.save(update_fields=['total_price'])

        # Данные для отзыва
        review_data = {
            'product': self.product2.slug,
            'comment': 'test review comment',
            'rating': 4,
        }

        # Неправильное создание отзыва и проверка
        invalid_normal_response = self.normal_client.post(
            self.reviews_list_url, data=review_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_normal_response.data['product'][0], 'Вам не доставляли этот товар')
    
    def test_admin_user_can_create_review_if_product_is_not_delivered(self):
        # Создание недоставленного заказа
        not_delivered_order = Order.objects.create(
            order_id=uuid4(),
            user=self.admin_user,
            full_name='Test full name admin',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            total_price=Decimal('1.00'),
            status=StatusChoices.PENDING,
            yookassa_id=str(uuid4()),
        )

        # Создание единицы заказа
        OrderItem.objects.create(
            order=not_delivered_order,
            product=self.product2,
            price=self.product2.price,
            quantity=1,
        )
        
        # Перерасчет цены заказа
        not_delivered_order.total_price = not_delivered_order.total_price_after_discount
        not_delivered_order.save(update_fields=['total_price'])

        # Данные для отзыва
        review_data = {
            'product': self.product2.slug,
            'comment': 'test review comment',
            'rating': 4,
        }

        # Создание отзыва и проверка
        created_admin_response = self.admin_client.post(
            self.reviews_list_url, data=review_data,
        )
        self.assertEqual(created_admin_response.status_code, status.HTTP_201_CREATED)

        # Проверка на совпадение отзыва
        data = created_admin_response.data
        self.assertTrue(Review.objects.filter(id=data['id']).exists())

        # Проверка на совпадения в отзыве
        new_review = Review.objects.get(id=data['id'])
        self.check_review_in_review_data(review_data=data, review=new_review)
        review_product = new_review.product
        self.assertEqual(review_product.slug, data['product_slug'])
        self.assertEqual(review_product.title, data['product_title'])

    def test_normal_user_can_create_review(self):
        # Данные для отзыва
        review_data = {
            'product': self.product3.slug,
            'comment': 'test review comment',
            'rating': 4,
        }

        # Создание отзыва и проверка
        created_normal_response = self.normal_client.post(
            self.reviews_list_url, data=review_data,
        )
        self.assertEqual(created_normal_response.status_code, status.HTTP_201_CREATED)

        # Проверка на совпадение отзыва
        data = created_normal_response.data
        self.assertTrue(Review.objects.filter(id=data['id']).exists())

        # Проверка на совпадения в отзыве
        new_review = Review.objects.get(id=data['id'])
        self.check_review_in_review_data(review_data=data, review=new_review)
        review_product = new_review.product
        self.assertEqual(review_product.slug, data['product_slug'])
        self.assertEqual(review_product.title, data['product_title'])

    def test_anon_user_cannot_patch_review(self):
        # Данные для частичного изменения отзыва
        review_data = {
            'product': self.product1.slug,
            'comment': 'new test review comment',
        }
        
        # Неправильная попытка частично изменить отзыв и проверка
        invalid_anon_response = self.anon_client.patch(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk),
            data=review_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_patch_other_review(self):
        # Данные для частичного изменения отзыва
        review_data = {
            'comment': 'new test review comment',
        }
        
        # Неправильная попытка частично изменить отзыв и проверка
        invalid_normal_response = self.normal_client.patch(
            self.get_review_detail_with_pk(pk=self.product1_admin_review.pk),
            data=review_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_patch_other_review(self):
        # Записываем старый отзыв
        old_review = self.product1_normal_review

        # Данные для частичного изменения отзыва
        review_data = {
            'comment': 'new test review comment',
        }
        
        # Частичное измение отзыва и проверка
        updated_admin_response = self.admin_client.patch(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk),
            data=review_data,
        )
        self.assertEqual(updated_admin_response.status_code, status.HTTP_200_OK)

        # Проверка на измененность отзыва
        data = updated_admin_response.data
        self.assertTrue(Review.objects.filter(id=data['id']).exists())
        self.assertFalse(Review.objects.filter(
            user=self.admin_user, product=self.product1, comment=old_review.comment).exists()
        )

        # Проверка на совпадения в отзыве
        new_review = Review.objects.get(id=data['id'])
        self.check_review_in_review_data(review_data=data, review=new_review)
        review_product = new_review.product
        self.assertEqual(review_product.slug, data['product_slug'])
        self.assertEqual(review_product.title, data['product_title'])
        
        # Сравнение со старым отзывом
        self.assertEqual(new_review.rating, old_review.rating)
        self.assertNotEqual(new_review.comment, old_review.comment)

    def test_normal_user_can_patch_his_own_review(self):
        # Записываем старый отзыв
        old_review = self.product1_normal_review

        # Данные для частичного изменения отзыва
        review_data = {
            'comment': 'new test review comment',
        }
        
        # Частичное измение отзыва и проверка
        updated_normal_response = self.normal_client.patch(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk),
            data=review_data,
        )
        self.assertEqual(updated_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на измененность отзыва
        data = updated_normal_response.data
        self.assertTrue(Review.objects.filter(id=data['id']).exists())
        self.assertFalse(Review.objects.filter(
            user=self.normal_user, product=self.product1, comment=old_review.comment).exists()
        )

        # Проверка на совпадения в отзыве
        new_review = Review.objects.get(id=data['id'])
        self.check_review_in_review_data(review_data=data, review=new_review)
        review_product = new_review.product
        self.assertEqual(review_product.slug, data['product_slug'])
        self.assertEqual(review_product.title, data['product_title'])

        # Сравнение со старым отзывом
        self.assertEqual(new_review.rating, old_review.rating)
        self.assertNotEqual(new_review.comment, old_review.comment)

    def test_anon_user_cannot_put_review(self):
        # Данные для полного изменения отзыва
        review_data = {
            'product': self.product3.slug,
            'comment': 'new test review comment',
            'rating': 3,
        }
        
        # Неправильная попытка полностью изменить отзыв и проверка
        invalid_anon_response = self.anon_client.put(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk),
            data=review_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_put_other_review(self):
        # Данные для полного изменения отзыва
        review_data = {
            'product': self.product3.slug,
            'comment': 'new test review comment',
            'rating': 3,
        }
        
        # Неправильная попытка полностью изменить отзыв и проверка
        invalid_normal_response = self.normal_client.put(
            self.get_review_detail_with_pk(pk=self.product1_admin_review.pk),
            data=review_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_put_other_review(self):
        # Записываем старый отзыв
        old_review = self.product1_normal_review

        # Данные для полного изменения отзыва
        review_data = {
            'product': self.product3.slug,
            'comment': 'new test review comment',
            'rating': 3,
        }
        
        # Частичное измение отзыва и проверка
        updated_admin_response = self.admin_client.put(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk),
            data=review_data,
        )
        self.assertEqual(updated_admin_response.status_code, status.HTTP_200_OK)

        # Проверка на измененность отзыва
        data = updated_admin_response.data
        self.assertTrue(Review.objects.filter(id=data['id']).exists())
        self.assertFalse(Review.objects.filter(
            user=self.normal_user, product=self.product1).exists()
        )

        # Проверка на совпадения в ответе отзыва
        new_review = Review.objects.get(id=data['id'])
        review_product = new_review.product
        self.assertEqual(review_product.slug, data['product_slug'])
        self.assertEqual(review_product.title, data['product_title'])
        
        # Сравнение со старым отзывом
        self.assertNotEqual(review_product.slug, old_review.product.slug)

    def test_normal_user_can_put_his_own_review(self):
        # Записываем старый отзыв
        old_review = self.product1_normal_review

        # Данные для полного изменения отзыва
        review_data = {
            'product': self.product3.slug,
            'comment': 'new test review comment',
            'rating': 3,
        }
        
        # Полное измение отзыва и проверка
        updated_normal_response = self.normal_client.put(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk),
            data=review_data,
        )
        self.assertEqual(updated_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на измененность отзыва
        data = updated_normal_response.data
        self.assertTrue(Review.objects.filter(id=data['id']).exists())
        self.assertFalse(Review.objects.filter(
            user=self.normal_user, product=self.product1).exists()
        )

        # Проверка на совпадения в ответе отзыва
        new_review = Review.objects.get(id=data['id'])
        review_product = new_review.product
        self.assertEqual(review_product.slug, data['product_slug'])
        self.assertEqual(review_product.title, data['product_title'])
        
        # Сравнение со старым отзывом
        self.assertNotEqual(review_product.slug, old_review.product.slug)

    def test_anon_user_cannot_delete_review(self):
        # Неправильное удаление отзыва и проверка
        invalid_anon_response = self.anon_client.delete(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk)
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_delete_other_review(self):
        # Неправильное удаление отзыва и проверка
        invalid_normal_response = self.normal_client.delete(
            self.get_review_detail_with_pk(pk=self.product1_admin_review.pk)
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_user_can_delete_other_review(self):
        # Удаление отзыва и проверка
        deleted_admin_response = self.admin_client.delete(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk)
        )
        self.assertEqual(deleted_admin_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на несуществование отзыва
        self.assertFalse(Review.objects.filter(id=self.product1_normal_review.pk).exists())
    
    def test_normal_user_can_delete_his_own_review(self):
        # Удаление отзыва и проверка
        deleted_normal_response = self.normal_client.delete(
            self.get_review_detail_with_pk(pk=self.product1_normal_review.pk)
        )
        self.assertEqual(deleted_normal_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на несуществование отзыва
        self.assertFalse(Review.objects.filter(id=self.product1_normal_review.pk).exists())
