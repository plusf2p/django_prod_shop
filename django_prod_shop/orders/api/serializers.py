from rest_framework import serializers

from django.db.models import Prefetch

from django_prod_shop.cart.models import Cart, CartItem
from django_prod_shop.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.SlugRelatedField(read_only=True, slug_field='product.slug')

    class Meta:
        model = OrderItem
        fields = ['order', 'product_slug', 'price', 'quantity', 'cost']


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='items', many=True, read_only=True)
    total_price_before_discount = serializers.SerializerMethodField(read_only=True)
    discount_price = serializers.SerializerMethodField(read_only=True)
    total_price_after_discount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'items', 'user', 'full_name', 'phone', 'address', 'city',
            'discount', 'status', 'created_at', 'updated_at', 'total_price',
            'total_price_before_discount', 'discount_price', 'total_price_after_discount',
        ]
        read_only_fields = [
            'id', 'user', 'discount', 'status', 'created_at', 'updated_at', 'total_price',
            'total_price_before_discount', 'discount_price', 'total_price_after_discount',
        ]
    
    def get_total_price_before_discount(self, obj):
        return obj.total_price_before_discount
    
    def get_discount_price(self, obj):
        return obj.discount_price
    
    def get_total_price_after_discount(self, obj):
        return obj.total_price_after_discount


class OrderWriteSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='items', many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'items', 'user', 'full_name', 'phone', 'address', 'city',
            'discount', 'status', 'created_at', 'updated_at', 'total_price',
        ]
        read_only_fields = ['status']

    def create(self, validated_data):
        items = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        user = validated_data.pop('user')

        for item in items:
            OrderItem.objects.create(order=order, **item)
        
        cart = Cart.objects.select_related('user').prefetch_related(
            Prefetch('items', queryset=CartItem.objects.select_related('product'))
        ).filter(user=user)
        cart.items.all().delete()
        cart.delete()

        return order
