from rest_framework import serializers

from django_prod_shop.products.models import Product
from django_prod_shop.cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product_title', 'quantity', 'total_price']
    
    def validate(self, attrs):
        quantity = attrs.get('quantity')
        
        if quantity is None:
            raise serializers.ValidationError({'quantity': 'Укажите количество'})

        if quantity < 0:
            raise serializers.ValidationError({'quantity': 'Количество не может быть меньше 0'})
        
        if quantity == 0:
            raise serializers.ValidationError({'quantity': 'Количество не может равняться 0'})

        return attrs


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
            
        quantity = attrs.get('quantity')
        if quantity is None:
            raise serializers.ValidationError({'quantity': 'Укажите количество'})

        available_quantity = product.quantity - product.reserved_quantity
        if available_quantity < quantity:
            raise serializers.ValidationError({
                'quantity': 'Недостаточно товара на складе'
            })
        
        self.context['product'] = product
        return attrs


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)
