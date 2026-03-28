from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django_prod_shop.users.models import User, Profile


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['full_name'] = user.profile.full_name
        token['email'] = user.email
        token['phone'] = user.profile.phone
        token['city'] = user.profile.city
        token['address'] = user.profile.address

        return token


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ['email', 'full_name', 'phone', 'city', 'address']


class RegisterProfileSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    password1 = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    
    def validate(self, attrs):
        password1 = attrs.get('password1')
        password2 = attrs.get('password2')

        if password1 is None:
            raise serializers.ValidationError({'password1': 'Укажите пароль'})
        
        if password2 is None:
            raise serializers.ValidationError({'password2': 'Укажите повтор пароля'})

        if attrs['password1'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'Пароли не совпадают'})
        
        user_model = get_user_model()

        if user_model.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({'email': 'Такой email уже существует'})

        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        email = validated_data.pop('email')
        password1 = validated_data.pop('password1')

        user_model = get_user_model()
        new_user = user_model.objects.create_user(email=email, password=password1)

        if not Profile.objects.filter(user=new_user).exists():
            return Profile.objects.create(user=new_user, full_name='', phone='', city='', address='')
        
        return new_user.profile


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        request = self.context['request']

        if not request.user.check_password(value):
            raise serializers.ValidationError({'old_password': 'Неверный старый пароль'})

        return value

    def validate(self, attrs):
        new_password1 = attrs.get('new_password1')
        new_password2 = attrs.get('new_password2')

        if new_password1 is None:
            raise serializers.ValidationError({'new_password1': 'Укажите новый пароль'})
        
        if new_password2 is None:
            raise serializers.ValidationError({'new_password1': 'Укажите повтор пароля'})
        
        if new_password1 != new_password2:
            raise serializers.ValidationError({'new_password2': 'Пароли не сопадают'})

        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)

    def validate_email(self, value):
        user_model = get_user_model()

        if not user_model.objects.filter(email=value).exists():
            raise serializers.ValidationError({'email': 'Пользователя с таким email не существует'})
            
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        new_password1 = attrs.get('new_password1')
        new_password2 = attrs.get('new_password2')
        
        if new_password1 is None:
            raise serializers.ValidationError({'new_password1': 'Укажите новый пароль'})
        
        if new_password2 is None:
            raise serializers.ValidationError({'new_password1': 'Укажите повтор пароля'})
        
        if new_password1 != new_password2:
            raise serializers.ValidationError({'new_password2': 'Пароли не сопадают'})

        return attrs
