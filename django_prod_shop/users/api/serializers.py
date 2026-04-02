from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django_prod_shop.users.models import Profile

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        if user.profile_id:
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
