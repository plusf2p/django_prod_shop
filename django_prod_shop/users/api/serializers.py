from django.contrib.auth import get_user_model, authenticate
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
    
    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Пароли не совпадают.'})
        
        user_model = get_user_model()

        if user_model.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Такой email уже существует.'})

        return data
    
    @transaction.atomic
    def create(self, validated_data):
        email = validated_data.pop('email')
        password1 = validated_data.pop('password1')

        user_model = get_user_model()
        new_user = user_model.objects.create_user(email=email, password=password1)

        return Profile.objects.create(user=new_user, full_name='', phone='', city='', address='')
