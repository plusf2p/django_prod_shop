from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django_prod_shop.users.models import Profile

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email

        try:
            profile = user.profile
        except Profile.DoesNotExist:
            pass
        
        token['full_name'] = profile.full_name
        token['phone'] = profile.phone
        token['city'] = profile.city
        token['address'] = profile.address

        return token


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ['email', 'full_name', 'phone', 'city', 'address']
