from rest_framework import serializers

from django.db.models import Count, Avg

from django_prod_shop.reviews.api.serializers import ReviewSerializer
from django_prod_shop.products.models import Category, Product


class ProductReadSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.title', read_only=True)
    rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'category_name', 'slug', 'quantity', 'reserved_quantity', 
            'image', 'description', 'price', 'created_at', 'rating', 'reviews_count',
        ]
        read_only_fields = [
            'id', 'title', 'category_name', 'slug', 'quantity', 'reserved_quantity', 
            'image', 'description', 'price', 'created_at', 'rating', 'reviews_count',
        ]


class ProductWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source='category', queryset=Category.objects.all(), write_only=True,
    )

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'category_id', 'slug', 'quantity', 'reserved_quantity', 
            'image', 'description', 'price', 'is_active',
        ]
        read_only_fields = ['id']

    def validate_image(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError({'image': 'Максимальный размер изображения - 10 МБ'})

        if value.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
            raise serializers.ValidationError({'image': 'Допустимы только форматы: JPG, PNG, WEBP'})

        return value

    def validate(self, attrs):
        price = attrs.get('price', getattr(self.instance, 'price', None))
    
        if price is None:
            raise serializers.ValidationError({'price': 'Укажите цену'})

        if price < 0:
            raise serializers.ValidationError({'price': 'Цена не должна быть меньше 0'})

        quantity = attrs.get('quantity', getattr(self.instance, 'quantity', None))
        reserved_quantity = attrs.get('reserved_quantity', getattr(self.instance, 'reserved_quantity', None))

        if quantity is None:
            raise serializers.ValidationError({
                'quantity': 'Укажите количество доступного товара'
            })
        
        if reserved_quantity is None:
            raise serializers.ValidationError({
                'reserved_quantity': 'Укажите количество зарезервированного товара'
            })

        if quantity < reserved_quantity:
            raise serializers.ValidationError({
                'quantity': 'Недостаточно товара на складе'
            })

        return attrs


class SimilarProductSerializer(serializers.ModelSerializer):
    rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'image', 'price', 'rating', 'reviews_count',
        ]
        read_only_fields = [
            'id', 'title', 'slug', 'image', 'price', 'rating', 'reviews_count',
        ]


class ProductDetailSerializer(ProductReadSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    similar_products = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'category_name', 'slug', 'quantity', 'reserved_quantity', 'image', 'description', 
            'price', 'reviews', 'created_at', 'rating', 'reviews_count', 'similar_products',
        ]
        read_only_fields = [
            'id', 'title', 'category_name', 'slug', 'quantity', 'reserved_quantity', 'image', 'description', 
            'price', 'reviews', 'created_at', 'rating', 'reviews_count', 'similar_products',
        ]
    
    def get_similar_products(self, obj):
        if obj.category is None:
            return []

        result = Product.objects.annotate(
            rating=Avg('reviews__rating'), reviews_count=Count('reviews')
        ).filter(category=obj.category, is_active=True).exclude(
            id=obj.id
        ).order_by('-created_at')[:4]

        return SimilarProductSerializer(result, many=True).data


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title', 'description', 'slug', 'created_at']
        read_only_fields = ['id', 'title', 'description', 'slug', 'created_at']


class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['title', 'description', 'slug']


class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductReadSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'title', 'description', 'slug', 'products', 'created_at']
        read_only_fields = ['id', 'title', 'description', 'slug', 'products', 'created_at']
