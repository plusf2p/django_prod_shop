from rest_framework import serializers

from django_prod_shop.orders.api.serializers import OrderReadSerializer
from django_prod_shop.payment.models import Payment, StatusChoices


class PaymentSerializer(serializers.ModelSerializer):
    order = OrderReadSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['order', 'amount', 'payment_id', 'status', 'created_at']
        read_only_fields = ['amount', 'payment_id', 'status', 'created_at']

    def validate(self, attrs):
        status = attrs.get('status')

        if status is None:
            raise serializers.ValidationError({'status': 'Укажите статус'})

        if status not in [choice.value for choice in StatusChoices]:
            raise serializers.ValidationError({'status': 'Неверный статус платежа'})
        
        amount = attrs.get('amount')

        if amount is None:
            raise serializers.ValidationError({'amount': 'Укажите цену'})

        if amount < 0:
            raise serializers.ValidationError({'amount': 'Сумма не может быть меньше 0'})
        
        if amount == 0:
            raise serializers.ValidationError({'amount': 'Сумма не может быть равна 0'})

        return attrs
