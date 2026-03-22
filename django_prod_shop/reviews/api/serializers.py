from rest_framework import serializers

from django_prod_shop.orders.models import OrderItem, Order
from django_prod_shop.products.models import Product
from django_prod_shop.reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field='slug',
        write_only=True,
    )
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.SlugRelatedField(source='product', read_only=True, slug_field='slug')

    class Meta:
        model = Review
        fields = [
            'id', 'product', 'product_title', 'product_slug', 'user', 'comment', 
            'rating', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'product_title', 'user', 'created_at', 'updated_at']

    def validate(self, attrs):
        rating = attrs.get('rating')

        if rating is None:
            raise serializers.ValidationError('Укажите рейтинг')

        rating = attrs['rating']

        if not (1 <= rating <= 5):
            raise serializers.ValidationError('Рейтинг не может быть меньше 1 или больше 5')

        request = self.context['request']
        user = request.user
        product = attrs['product']

        if self.instance is None:
            if Review.objects.filter(product=product, user=user).exists():
                raise serializers.ValidationError('Вы уже оставляли отзыв на этот товаром')

        check_order_exists = OrderItem.objects.filter(
            order__user=user, product=product, order__status=Order.StatusChoices.DELIVERED
        ).exists()

        if not check_order_exists and not user.is_staff:
            raise serializers.ValidationError('Вы не доставляли этот товар')

        return attrs
