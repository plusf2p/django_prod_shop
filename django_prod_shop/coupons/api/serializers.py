from django.utils import timezone

from rest_framework import serializers

from django_prod_shop.coupons.models import Coupon


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount', 'valid_from', 'valid_to', 'is_active']

    def validate_discount(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError('Значение скидки должно быть от 0 до 100')
        
        return value

    def validate(self, attrs):
        now = timezone.now().date()

        instance = getattr(self, 'instance', None)
        valid_from = attrs.get('valid_from', getattr(instance, 'valid_from', None))
        valid_to = attrs.get('valid_to', getattr(instance, 'valid_to', None))

        if valid_from is None:
            raise serializers.ValidationError({'valid_from': 'Укажите дату начала работы купона'})
        
        if valid_to is None:
            raise serializers.ValidationError({'valid_to': 'Укажите дату конца работы купона'})
        
        if valid_from > now:
            raise serializers.ValidationError({'valid_from': 'Срок действия купона ещё не начался'})

        if valid_to < now:
            raise serializers.ValidationError({'valid_to': 'Срок действия купона истёк'})

        if valid_to <= valid_from:
            raise serializers.ValidationError({'valid_to': 'Дата начала работы купона не может быть позже даты конца работы'})

        return attrs
