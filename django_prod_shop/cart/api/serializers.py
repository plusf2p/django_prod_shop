from rest_framework import serializers

from django_prod_shop.products.models import Product
from django_prod_shop.cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['product', 'quantity', 'total_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cart_items', many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['items', 'total_price', 'total_quantity']
        read_only_fields = ['total_price', 'total_quantity']


class CartAddSerializer(serializers.Serializer):
    product_slug = serializers.SlugField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, attrs):
        try:
            product = Product.objects.get(slug=attrs['product_slug'], is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({'product_slug' :'Такого товара не существует'})
        
        available_quantity = product.quantity - product.reserved_quantity
        if available_quantity < attrs['quantity']:
            raise serializers.ValidationError({
                'quantity': 'Недостаточно товара на складе'
            })
        
        self.context['product'] = product
        return attrs


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)
