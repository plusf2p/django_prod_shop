from rest_framework import serializers

from django_prod_shop.orders.models import OrderItem, StatusChoices
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
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        error_messages={
            'min_value': 'Рейтинг не может быть меньше 1',
            'max_value': 'Рейтинг не может быть больше 5',
        },
    )

    class Meta:
        model = Review
        fields = [
            'id', 'product', 'product_title', 'product_slug', 'user', 
            'user_id', 'comment', 'rating', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context['request']
        user = request.user

        instance = getattr(self, 'instance', None)
        product = attrs.get('product', getattr(instance, 'product', None))

        if instance is None:
            if Review.objects.filter(product=product, user=user).exists():
                raise serializers.ValidationError({'product': 'Вы уже оставляли отзыв на этот товаром'})

        check_order_exists = OrderItem.objects.filter(
            order__user=user, product=product, order__status=StatusChoices.DELIVERED
        ).exists()

        if not check_order_exists and not user.is_staff:
            raise serializers.ValidationError({'product': 'Вам не доставляли этот товар'})

        return attrs
