from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Создание ролей Покупатель, Менеджер и Админ"

    def handle(self, *args, **options):
        ### Разрешения ###

        # Товары
        product_view = Permission.objects.get(codename='view_product')
        product_add = Permission.objects.get(codename='add_product')
        product_change = Permission.objects.get(codename='change_product')
        product_delete = Permission.objects.get(codename='delete_product')
        manage_products = Permission.objects.get(codename='manage_products')

        # Категории
        category_view = Permission.objects.get(codename='view_category')
        category_add = Permission.objects.get(codename='add_category')
        category_change = Permission.objects.get(codename='change_category')
        category_delete = Permission.objects.get(codename='delete_category')
        manage_categories = Permission.objects.get(codename='manage_categories')

        # Купоны
        coupon_view = Permission.objects.get(codename='view_coupon')
        coupon_add = Permission.objects.get(codename='add_coupon')
        coupon_change = Permission.objects.get(codename='change_coupon')
        coupon_delete = Permission.objects.get(codename='delete_coupon')
        manage_coupons = Permission.objects.get(codename='manage_coupons')

        # Отзывы
        review_view = Permission.objects.get(codename='view_review')
        review_add = Permission.objects.get(codename='add_review')
        review_change = Permission.objects.get(codename='change_review')
        review_delete = Permission.objects.get(codename='delete_review')
        manage_reviews = Permission.objects.get(codename='manage_reviews')

        # Заказы
        order_view = Permission.objects.get(codename='view_order')
        order_add = Permission.objects.get(codename='add_order')
        order_change = Permission.objects.get(codename='change_order')
        order_delete = Permission.objects.get(codename='delete_order')
        manage_orders = Permission.objects.get(codename='manage_orders')

        # Платежи
        payment_view = Permission.objects.get(codename='view_payment')
        payment_add = Permission.objects.get(codename='add_payment')
        payment_change = Permission.objects.get(codename='change_payment')
        payment_delete = Permission.objects.get(codename='delete_payment')
        manage_payments = Permission.objects.get(codename='manage_payments')

        ### Группы ###

        # Покупатель
        customers, created = Group.objects.get_or_create(name='Customers')
        customers.permissions.set([
            product_view,

            category_view,
            
            review_view,
            review_add,

            order_add,
        ])

        if created:
            self.stdout.write(
                self.style.SUCCESS('Роль Customer (Покупатель) создана.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Роль Customer (Покупатель) уже существует.')
            )

        # Менеджер
        manager, created = Group.objects.get_or_create(name='Manager')
        manager.permissions.set([
            product_view,
            product_add,
            product_change,
            product_delete,
            manage_products,

            category_view,
            category_add,
            category_change,
            category_delete,
            manage_categories,

            coupon_view,
            coupon_add,
            coupon_change,
            coupon_delete,
            manage_coupons,
            
            review_view,
            review_add,
            review_change,
            review_delete,
            manage_reviews,

            order_view,
            order_add,
            order_change,
            manage_orders,

            payment_view,
            payment_add,
        ])

        if created:
            self.stdout.write(
                self.style.SUCCESS('Роль Manager (Менеджер) создана.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Роль Manager (Менеджер) уже существует.')
            )

        # Админ
        admin, created = Group.objects.get_or_create(name='Admin')
        admin.permissions.set([
            product_view,
            product_add,
            product_change,
            product_delete,
            manage_products,

            category_view,
            category_add,
            category_change,
            category_delete,
            manage_categories,

            coupon_view,
            coupon_add,
            coupon_change,
            coupon_delete,
            manage_coupons,
            
            review_view,
            review_add,
            review_change,
            review_delete,
            manage_reviews,

            order_view,
            order_add,
            order_change,
            order_delete,
            manage_orders,

            payment_view,
            payment_add,
            payment_change,
            payment_delete,
            manage_payments,
        ])

        if created:
            self.stdout.write(
                self.style.SUCCESS('Роль Admin (Админ) создана.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Роль Admin (Админ) уже существует.')
            )
