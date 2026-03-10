from rest_framework import serializers

from django_prod_shop.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.SlugRelatedField(read_only=True, slug_field='product.slug')

    class Meta:
        model = OrderItem
        fields = ['order', 'product_slug', 'price', 'quantity', 'cost']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='items', many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'items', 'user', 'full_name', 'phone', 'address', 'city',
            'discount', 'status', 'created_at', 'updated_at', 'total_price', 
            'total_price_before_discount', 'discount_price', 'total_price_after_discount',
        ]
        read_only_fields = [
            'id', 'user', 'full_name', 'phone', 'address', 'city', 'discount',
            'status', 'created_at', 'updated_at', 'total_price', 
            'total_price_before_discount', 'discount_price', 'total_price_after_discount',
        ]


class OrderUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=250)
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=250)
    city = serializers.CharField(max_length=100)
    discount = serializers.IntegerField(default=0)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    stats = serializers.CharField(max_length=20)
