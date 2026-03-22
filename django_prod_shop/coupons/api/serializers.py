from rest_framework import serializers

from django_prod_shop.coupons.models import Coupon


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'discount', 'valid_from', 'valid_to', 'is_active']

    def validate(self, attrs):
        validate_from = attrs.get('validate_from')
        validate_to = attrs.get('validate_to')

        if validate_from is None:
            raise serializers.ValidationError('Укажите дату начала работы купона')
        
        if validate_to is None:
            raise serializers.ValidationError('Укажите дату конца работы купона')
            
        if validate_from > validate_to:
            raise serializers.ValidationError('Дата начала работы купона не может быть позже даты конца работы')

        return attrs
