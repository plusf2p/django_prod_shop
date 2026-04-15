from django.utils import timezone

from rest_framework import serializers

from django_prod_shop.coupons.models import Coupon
from django_prod_shop.products.models import Product
from django_prod_shop.cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.SlugRelatedField(source='product', slug_field='slug', read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'product_title', 'product_slug', 'quantity', 'total_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cart_items', many=True, read_only=True)
    coupon = serializers.CharField(source='coupon.code', read_only=True)
    discount = serializers.IntegerField(source='coupon.discount', read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['items', 'total_price', 'total_quantity', 'coupon', 'discount']


class CartAddSerializer(serializers.Serializer):
    product_slug = serializers.SlugField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, attrs):
        try:
            product = Product.objects.get(slug=attrs['product_slug'], is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({'product_slug' :'Такого товара не существует'})
            
        quantity = attrs['quantity']
        available_quantity = product.quantity - product.reserved_quantity
        if available_quantity < quantity:
            raise serializers.ValidationError({
                'quantity': 'Недостаточно товара на складе'
            })
        
        self.context['product'] = product
        return attrs


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate(self, attrs):
        code = attrs['code']
        now = timezone.now().date()

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError({
                'code': 'Такого купона не существует'
            })

        if not coupon.is_active:
            raise serializers.ValidationError({
                'code': 'Данный купон неактивен'
            })

        if coupon.valid_from > now:
            raise serializers.ValidationError({
                'code': 'Срок действия купона ещё не начался'
            })

        if coupon.valid_to < now:
            raise serializers.ValidationError({
                'code': 'Срок действия купона истёк'
            })

        self.context['coupon'] = coupon
        return attrs
