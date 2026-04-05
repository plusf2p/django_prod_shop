from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django_prod_shop.users.models import Profile

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email

        profile = getattr(user, 'profile', None)
        
        token['full_name'] = profile.full_name if profile else ''
        token['phone'] = profile.phone if profile else ''
        token['city'] = profile.city if profile else ''
        token['address'] = profile.address if profile else ''

        return token


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ['email', 'full_name', 'phone', 'city', 'address']
