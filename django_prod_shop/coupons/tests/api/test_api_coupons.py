from datetime import timedelta, date
from uuid import uuid4
from typing import Any

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from django.urls import reverse


from rest_framework.test import APITestCase, APIClient
from rest_framework.response import Response
from rest_framework import status

from django_prod_shop.coupons.models import Coupon


user_model = get_user_model()


class CouponAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Создание ролей
        call_command('create_groups')

        ### Users ###

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

        # Создание менеджера
        cls.manager_user_data = {
            'email': 'test_manager1@mail.ru',
            'password': 'test_manager1_password!',
        }
        cls.manager_user = user_model.objects.create_user(
            email=cls.manager_user_data['email'], 
            password=cls.manager_user_data['password'],
            is_active=True,
        )
        # Назначение роли менеджера менеджеру
        group, _ = Group.objects.get_or_create(name='Manager')
        cls.manager_user.groups.add(group)

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
        cls.list_coupons_url = reverse('coupons:coupons-list')

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
        cls.coupon_future = Coupon.objects.create(
            code='test-coupon-future',
            valid_from=time_start + timedelta(days=10),
            valid_to=time_start + timedelta(days=11),
            discount=50,
            is_active=True,
        )
        cls.coupon_past = Coupon.objects.create(
            code='test-coupon-past',
            valid_from=time_start - timedelta(days=11),
            valid_to=time_start - timedelta(days=10),
            discount=50,
            is_active=True,
        )
        
    def setUp(self) -> None:
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.manager_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.normal_client.force_authenticate(user=self.normal_user)
        self.manager_client.force_authenticate(user=self.manager_user)
        self.admin_client.force_authenticate(user=self.admin_user)

    def get_coupon_detail_url_with_kwargs(self, code: str) -> str:
        return reverse('coupons:coupons-detail', kwargs={'code': code})

    def get_list_items(self, coupons_response: Response) -> list[dict[str, Any]]:
        if 'results' in coupons_response.data:
            return coupons_response.data['results']
        return coupons_response.data

    def get_item_in_list(self, coupon_response: Response, code: str) -> dict[str, Any]:
        for item in self.get_list_items(coupon_response):
            if item['code'] == code:
                return item
        self.fail(f"Купон '{code}' не найден в ответе")

    def check_coupon_in_coupon_data(self, coupon_data: dict[str, Any], coupon: Coupon) -> None:
        self.assertEqual(coupon_data['code'], coupon.code)
        self.assertEqual(coupon_data['discount'], coupon.discount)
        self.assertEqual(
            coupon_data['valid_from'],
            self.bring_date_to_correct_form(coupon.valid_from),
        )
        self.assertEqual(
            coupon_data['valid_to'],
            self.bring_date_to_correct_form(coupon.valid_to),
        )
        self.assertEqual(coupon_data['is_active'], coupon.is_active)
    
    def check_coupon_from_db(self, code: str, **data: Any) -> Coupon:
        self.assertTrue(Coupon.objects.filter(code=code).exists())
        coupon = Coupon.objects.get(code=code)
        self.assertEqual(coupon.code, code)

        for key, value in data.items():
            self.assertEqual(getattr(coupon, key), value)
        
        return coupon

    def bring_date_to_correct_form(self, date: date) -> str:
        return date.strftime("%Y-%m-%d")

    def update_coupon_data(self, **new_data: Any) -> dict[str, Any]:
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()
        data = {
            'code': f'test-{uuid4().hex[:8]}',
            'valid_from': time_start,
            'valid_to': time_end,
            'discount': 25,
            'is_active': True,
        }
        data.update(new_data)
        return data

    def test_anon_user_cannot_get_coupons_list(self) -> None:
        # Неправильная попытка получить список купонов анонимно и проверка
        invalid_anon_response = self.anon_client.get(self.list_coupons_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_get_coupons_list(self) -> None:
        # Неправильная попытка получить список купонов обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.get(self.list_coupons_url)
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def _check__admin_or_manager_user_can_get_list_of_all_coupons(self, client: APIClient) -> None:
        # Получение списка купонов и проверка
        list_response = client.get(self.list_coupons_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Получение и проверка первого правильного купона
        coupon1_data = self.get_item_in_list(
            coupon_response=list_response, code=self.coupon1.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon1_data, coupon=self.coupon1)

        # Получение и проверка второго правильного купона
        coupon2_data = self.get_item_in_list(
            coupon_response=list_response, code=self.coupon2.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon2_data, coupon=self.coupon2)

        # Получение и проверка неактивного купона
        coupon_inactive_data = self.get_item_in_list(
            coupon_response=list_response, code=self.coupon_inactive.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon_inactive_data, coupon=self.coupon_inactive)

        # Получение и проверка первого непарвильного купона
        coupon_past_data = self.get_item_in_list(
            coupon_response=list_response, code=self.coupon_past.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon_past_data, coupon=self.coupon_past)

        # Получение и проверка второго непарвильного купона
        coupon_future_data = self.get_item_in_list(
            coupon_response=list_response, code=self.coupon_future.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon_future_data, coupon=self.coupon_future)

    def test_admin_user_can_get_list_of_all_coupons(self) -> None:
        self._check__admin_or_manager_user_can_get_list_of_all_coupons(self.admin_client)

    def test_manager_user_can_get_list_of_all_coupons(self) -> None:
        self._check__admin_or_manager_user_can_get_list_of_all_coupons(self.manager_client)

    def test_anon_user_cannot_get_coupon_detail(self) -> None:
        # Неправильная попытка получить купон анонимно и проверка
        invalid_anon_response = self.anon_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_get_coupon_detail(self) -> None:
        # Неправильная попытка получить купон обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_cannot_get_not_exists_coupon_detail(self) -> None:
        # Неправильная попытка получить купон админом и проверка
        invalid_normal_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code='test-not-exists-code'),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_404_NOT_FOUND)

    def _check_admin_or_manager_user_can_get_any_coupon_detail(self, client: APIClient) -> None:
        # Получение обычного купона и проверка
        detail_response = client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=detail_response.data, coupon=self.coupon1)

         # Получение неактивного купона и проверка
        inactive_detail_response = client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon_inactive.code),
        )
        self.assertEqual(inactive_detail_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=inactive_detail_response.data, coupon=self.coupon_inactive)

         # Получение первого неправильного купона и проверка
        past_detail_response = client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon_past.code),
        )
        self.assertEqual(past_detail_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=past_detail_response.data, coupon=self.coupon_past)

         # Получение второго неправильного купона и проверка
        future_detail_response = client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon_future.code),
        )
        self.assertEqual(future_detail_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=future_detail_response.data, coupon=self.coupon_future)

    def test_admin_user_can_get_any_coupon_detail(self) -> None:
        self._check_admin_or_manager_user_can_get_any_coupon_detail(self.admin_client)

    def test_manager_user_can_get_any_coupon_detail(self) -> None:
        self._check_admin_or_manager_user_can_get_any_coupon_detail(self.manager_client)

    def test_anon_user_cannot_create_coupon(self) -> None:
        # Данные для создания купона
        test_coupon_data = self.update_coupon_data()

        # Неправильная попытка создать купон анонимно и проверка
        invalid_anon_response = self.anon_client.post(
            self.list_coupons_url, data=test_coupon_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_create_coupon(self) -> None:
        # Данные для создания купона
        test_coupon_data = self.update_coupon_data()

        # Неправильная попытка создать купон обычным пользователем и проверка
        invalid_normal_response = self.normal_client.post(
            self.list_coupons_url, data=test_coupon_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_cannot_create_coupon_with_exists_code(self) -> None:
        # Правильное время для купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = self.update_coupon_data(
            code=self.coupon2.code,
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
        )

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('code', invalid_admin_response.data)

    def test_admin_user_cannot_create_coupon_with_discount_lt_0(self) -> None:
        # Неправильные данные для создания купона
        invalid_test_coupon_data = self.update_coupon_data(
            discount=-1,
        )

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertIn('discount', invalid_admin_response.data)
    
    def test_admin_user_cannot_create_coupon_with_discount_gt_100(self) -> None:
        # Неправильные данные для создания купона
        invalid_test_coupon_data = self.update_coupon_data(
            discount=101,
        )

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertIn('discount', invalid_admin_response.data)

    def test_admin_user_cannot_create_coupon_with_invalid_code(self) -> None:
        # Правильное время для купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = self.update_coupon_data(
            code='',
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
        )

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('code', invalid_admin_response.data)

    def test_admin_user_cannot_create_coupon_with_invalid_date_from(self) -> None:
        # Неправильное время для купонов
        time_start = (timezone.now() + timedelta(days=7)).date()
        time_end = timezone.now().date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = self.update_coupon_data(
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
        )

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('valid_from', invalid_admin_response.data)

    def test_admin_user_cannot_create_coupon_with_invalid_date_to(self) -> None:
        # Неправильное время для купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() - timedelta(days=7)).date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = self.update_coupon_data(
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
        )

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('valid_to', invalid_admin_response.data)

    def _check_admin_or_manager_user_can_create_coupon(self, client: APIClient) -> None:
        # Данные для создания купона
        test_coupon_data = self.update_coupon_data()

        # Создание купона и проверка
        response = client.post(
            self.list_coupons_url, data=test_coupon_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], test_coupon_data['code'])
        self.assertEqual(
            response.data['valid_from'], 
            self.bring_date_to_correct_form(test_coupon_data['valid_from']),
        )
        self.assertEqual(
            response.data['valid_to'], 
            self.bring_date_to_correct_form(test_coupon_data['valid_to']),
        )
        self.assertEqual(response.data['discount'], test_coupon_data['discount'])
        self.assertEqual(response.data['is_active'], test_coupon_data['is_active'])

        # Проверка нового купона
        new_coupon = self.check_coupon_from_db(
            code=test_coupon_data['code'],
            valid_from=test_coupon_data['valid_from'],
            valid_to=test_coupon_data['valid_to'],
            discount=test_coupon_data['discount'],
            is_active=test_coupon_data['is_active'],
        )

        # Получение нового купона и проверка
        detail_response = client.get(
            self.get_coupon_detail_url_with_kwargs(code=test_coupon_data['code']),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=detail_response.data, coupon=new_coupon)

    def test_admin_user_can_create_coupon(self) -> None:
        self._check_admin_or_manager_user_can_create_coupon(self.admin_client)
    
    def test_manager_user_can_create_coupon(self) -> None:
        self._check_admin_or_manager_user_can_create_coupon(self.manager_client)

    def test_anon_user_cannot_put_coupon(self) -> None:
        # Данные для полного обновления купона
        test_coupon_data = self.update_coupon_data()

        # Неправильная полностью обновить купон анонимно и проверка
        invalid_anon_response = self.anon_client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
            data=test_coupon_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())
    
    def test_normal_user_cannot_put_coupon(self) -> None:
        # Данные для полного обновления купона
        test_coupon_data = self.update_coupon_data()

        # Неправильная попытка полностью обновить купон обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
            data=test_coupon_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())

    def test_admin_user_cannot_put_coupon_with_exists_code(self) -> None:
        # Правильное время для купона
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Неправильные данные для полного обновления купона
        invalid_test_coupon_data = self.update_coupon_data(
            code=self.coupon2.code,
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
            is_active=False,
        )

        # Неправльное полное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('code', invalid_admin_response.data)

        # Проверка на необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())

    def test_admin_user_cannot_put_coupon_with_invalid_date_from(self) -> None:
        # Неправильное время для купона
        time_start = (timezone.now() + timedelta(days=7)).date()
        time_end = timezone.now().date()

        # Неправильные данные для полного обновления купона
        invalid_test_coupon_data = self.update_coupon_data(
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
            is_active=False,
        )

        # Неправльное полное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('valid_from', invalid_admin_response.data)

        # Проверка на необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())
    
    def test_admin_user_cannot_put_coupon_with_invalid_discount(self) -> None:
        # Правильное время для купона
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Неправильные данные для полного обновления купона
        invalid_test_coupon_data = self.update_coupon_data(
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
            is_active=False,
            discount=-1,
        )

        # Неправльное полное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertIn('discount', invalid_admin_response.data)

        # Проверка на необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(
            code=self.coupon1.code, discount=self.coupon1.discount
        ).exists())

    def test_admin_user_cannot_put_coupon_with_invalid_date_to(self) -> None:
        # Неправильное время для купона
        time_start = timezone.now().date()
        time_end = (timezone.now() - timedelta(days=7)).date()

        # Неправильные данные для полного обновления купона
        invalid_test_coupon_data = self.update_coupon_data(
            valid_from=self.bring_date_to_correct_form(time_start),
            valid_to=self.bring_date_to_correct_form(time_end),
            is_active=False,
        )

        # Неправльное полное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('valid_to', invalid_admin_response.data)

        # Проверка на необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())

    def _check_admin_or_manager_user_can_put_coupon(self, client: APIClient) -> None:
        # Данные для полного обновления купона
        test_coupon_data = self.update_coupon_data()

        # Старый код купона
        old_code = self.coupon1.code

        # Полное обновление купона админом и проверка
        admin_response = client.put(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=test_coupon_data,
        )
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)

        # Проверка обновленного купона
        self.check_coupon_from_db(
            code=test_coupon_data['code'],
            valid_from=test_coupon_data['valid_from'],
            valid_to=test_coupon_data['valid_to'],
            discount=test_coupon_data['discount'],
            is_active=test_coupon_data['is_active'],
        )

        # Проверка полностью обновленного купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(code=old_code).exists())

    def test_admin_user_can_put_coupon(self) -> None:
        self._check_admin_or_manager_user_can_put_coupon(self.admin_client)
    
    def test_manager_user_can_put_coupon(self) -> None:
        self._check_admin_or_manager_user_can_put_coupon(self.manager_client)
    
    def test_anon_user_cannot_patch_coupon(self) -> None:
        # Данные для частичного обновления купона
        test_coupon_data = {
            'code': self.coupon1.code,
            'discount': 1,
        }

        # Неправильная попытка частично обновить купон анонимно и проверка
        invalid_anon_response = self.anon_client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
            data=test_coupon_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка необновленность купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(
            code=self.coupon1.code, discount=test_coupon_data['discount'],
        ).exists())
    
    def test_normal_user_cannot_patch_coupon(self) -> None:
        # Даннын для частичного обновления купона
        test_coupon_data = {
            'code': self.coupon1.code,
            'discount': 1,
        }

        # Неправильная попытка частично обновить купон обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
            data=test_coupon_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка необновленность купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(
            code=self.coupon1.code, discount=test_coupon_data['discount']
        ).exists())

    def test_admin_user_cannot_patch_coupon_with_invalid_date_from(self) -> None:
        # Неправильное время для купона
        time_start = (timezone.now() + timedelta(days=7)).date()

        # Неправильные данные для частичного обновления купона
        invalid_test_coupon_data = {
            'valid_from': self.bring_date_to_correct_form(time_start),
        }

        # Неправльное частичное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('valid_from', invalid_admin_response.data)
        
        # Проверка необновленность купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(
            code=self.coupon1.code, 
            valid_from=self.bring_date_to_correct_form(time_start),
        ).exists())

    def test_admin_user_cannot_patch_coupon_with_invalid_date_to(self) -> None:
        # Неправильное время для купона
        time_end = (timezone.now() - timedelta(days=7)).date()

        # Неправильные данные для частичного обновления купона
        invalid_test_coupon_data = {
            'valid_to': self.bring_date_to_correct_form(time_end),
        }

        # Неправльное частичное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('valid_to', invalid_admin_response.data)
        
        # Проверка необновленность купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(
            code=self.coupon1.code, 
            valid_to=self.bring_date_to_correct_form(time_end),
        ).exists())
    
    def test_admin_user_cannot_patch_coupon_with_invalid_discount(self) -> None:
        # Неправильные данные для частичного обновления купона
        invalid_test_coupon_data = {
            'discount': -1,
        }

        # Неправльное частичное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertIn('discount', invalid_admin_response.data)
        
        # Проверка необновленность купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(
            code=self.coupon1.code, 
            discount=invalid_test_coupon_data['discount'],
        ).exists())
    
    def test_admin_user_cannot_patch_coupon_with_exists_code(self) -> None:
        # Неправильные данные для частичного обновления купона
        invalid_test_coupon_data = {
            'code': self.coupon2.code,
        }

        # Неправльное частичное обновление купона админом и проверка
        invalid_admin_response = self.admin_client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertNotIn('discount', invalid_admin_response.data)
        self.assertIn('code', invalid_admin_response.data)
        
        # Проверка необновленность купона
        self.coupon1.refresh_from_db()
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code, ).exists())

    def _check_admin_or_manager_user_can_patch_coupon(self, client: APIClient) -> None:
        # Данные для частичного обновления купона
        test_coupon_data = {
            'is_active': False,
        }

        # Частичное обновление купона админом и проверка
        response = client.patch(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code), 
            data=test_coupon_data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка обновленного купона
        self.check_coupon_from_db(
            code=self.coupon1.code,
            valid_from=self.coupon1.valid_from,
            valid_to=self.coupon1.valid_to,
            discount=self.coupon1.discount,
            is_active=test_coupon_data['is_active'],
        )

        # Проверка полностью обновленного купона
        self.coupon1.refresh_from_db()
        self.assertFalse(Coupon.objects.filter(code=self.coupon1.code, is_active=True).exists())

    def test_admin_user_can_patch_coupon(self) -> None:
        self._check_admin_or_manager_user_can_patch_coupon(self.admin_client)
    
    def test_manager_user_can_patch_coupon(self) -> None:
        self._check_admin_or_manager_user_can_patch_coupon(self.manager_client)

    def test_anon_user_cannot_delete_coupon(self) -> None:
        # Неправильная попытка удалить купон анонимно и проверка
        invalid_anon_response = self.anon_client.delete(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Проверка на наличие купона
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())
    
    def test_normal_user_cannot_delete_coupon(self) -> None:
        # Неправильная попытка удалить купон обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.delete(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на наличие купона
        self.assertTrue(Coupon.objects.filter(code=self.coupon1.code).exists())

    def _check_admin_or_manager_user_can_delete_coupon(self, client: APIClient) -> None:
        # Удаление обычного купона админом или менеджером и проверка
        delete_response = client.delete(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Попытка получить удаленный купон и проверка
        delete_response = client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)

        # Проверка на наличие купона
        self.assertFalse(Coupon.objects.filter(code=self.coupon1.code).exists())

    def test_admin_user_can_delete_coupon(self) -> None:
        self._check_admin_or_manager_user_can_delete_coupon(self.admin_client)

    def test_manager_user_can_delete_coupon(self) -> None:
        self._check_admin_or_manager_user_can_delete_coupon(self.manager_client)
