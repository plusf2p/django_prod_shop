from rest_framework import serializers

from django_prod_shop.reviews.api.serializers import ReviewSerializer
from django_prod_shop.products.models import Category, Product


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.title', read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source='category', queryset=Category.objects.all(), write_only=True,
    )
    reviews = ReviewSerializer(many=True, read_only=True)
    rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'title', 'category_name', 'category_id', 'slug', 'quantity', 'reserved_quantity', 'image',
            'description', 'price', 'reviews', 'created_at', 'rating', 'reviews_count', 'is_active',
            ]
        read_only_fields = ['created_at', 'sell_counter']

    def validate(self, attrs):
        price = attrs.get('price')

        if price is None:
            raise serializers.ValidationError({'price': 'Укажите цену'})

        if price < 0:
            raise serializers.ValidationError({'price': 'Цена не должна быть меньше 0'})

        quantity = attrs.get('quantity')
        reserved_quantity = attrs.get('reserved_quantity')

        if quantity is None:
            raise serializers.ValidationError({
                'quantity': 'Укажите количество доступного товара'
            })
        
        if reserved_quantity is None:
            raise serializers.ValidationError({
                'reserved_quantity': 'Укажите количество зарезервированного товара'
            })

        if attrs['quantity'] < attrs['reserved_quantity']:
            raise serializers.ValidationError({
                'quantity': 'Недостаточно товара на складе'
            })

        return attrs


class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['title', 'description', 'slug', 'products', 'created_at']
        read_only_fields = ['created_at']
