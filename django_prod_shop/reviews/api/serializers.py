from rest_framework import serializers

from django_prod_shop.reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.SlugRelatedField(source='product', read_only=True, slug_field='slug')

    class Meta:
        model = Review
        fields = ['product_title', 'product_slug', 'user', 'comment', 'rating', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']
