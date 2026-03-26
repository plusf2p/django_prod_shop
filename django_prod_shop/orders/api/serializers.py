from rest_framework import serializers

from django.db import transaction

from django_prod_shop.orders.models import Order, OrderItem
from django_prod_shop.orders.services import create_order
from django_prod_shop.orders.tasks import send_order_email


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.SlugRelatedField(source='product', slug_field='slug', read_only=True)
    cost = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['product_title', 'product_slug', 'price', 'quantity', 'cost']

    def get_cost(self, obj):
        return obj.cost


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon = serializers.CharField(source='coupon.code', read_only=True)
    total_price_before_discount = serializers.SerializerMethodField(read_only=True)
    discount_price = serializers.SerializerMethodField(read_only=True)
    total_price_after_discount = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'items', 'user', 'full_name', 'phone', 'address', 'city',
            'status', 'created_at', 'updated_at', 'total_price', 'coupon',
            'total_price_before_discount', 'discount_price', 'total_price_after_discount',
        ]
        read_only_fields = [
            'order_id', 'items', 'user', 'full_name', 'phone', 'address', 'city',
            'status', 'created_at', 'updated_at', 'total_price',
        ]
    
    def get_total_price_before_discount(self, obj):
        return obj.total_price_before_discount
    
    def get_discount_price(self, obj):
        return obj.discount_price
    
    def get_total_price_after_discount(self, obj):
        return obj.total_price_after_discount


class OrderWriteSerializer(serializers.ModelSerializer):
    coupon = serializers.CharField(source='coupon.code', read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'full_name', 'phone', 'address', 'city', 'coupon',
            'status', 'created_at', 'updated_at', 'total_price',
        ]
        read_only_fields = ['order_id', 'status', 'coupon', 'created_at', 'updated_at', 'total_price']

    def create(self, validated_data):
        order =  create_order(user=self.context['request'].user, validated_data=validated_data)
        transaction.on_commit(lambda: send_order_email.delay(str(order.order_id)))

        return order
