from rest_framework import serializers

from django_prod_shop.coupons.models import Coupon


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'discount', 'valid_from', 'valid_to', 'is_active']

    def validate(self, attrs):
        valid_from = attrs.get('valid_from')
        valid_to = attrs.get('valid_to')

        if valid_from is None:
            raise serializers.ValidationError({'valid_from': 'Укажите дату начала работы купона'})
        
        if valid_to is None:
            raise serializers.ValidationError({'valid_to': 'Укажите дату конца работы купона'})
            
        if valid_from > valid_to:
            raise serializers.ValidationError({'valid_to': 'Дата начала работы купона не может быть позже даты конца работы'})

        return attrs
