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
            'title', 'category_name', 'category_id', 'quantity', 'reserved_quantity', 'image', 'description', 
            'slug', 'price', 'reviews', 'created_at', 'rating', 'reviews_count', 'sell_counter', 'is_active',
            ]
        read_only_fields = ['created_at', 'sell_counter']


class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['title', 'description', 'slug', 'products', 'created_at']
        read_only_fields = ['created_at']
