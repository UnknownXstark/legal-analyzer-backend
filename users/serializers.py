# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# from django.contrib.auth.hashers import make_password
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth.tokens import PasswordResetTokenGenerator
# from django.utils.encoding import force_bytes, force_str
# from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import ClientAssignment, User

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        # Hash the password before saving
        validated_data['password'] = make_password(validated_data['password'])
        user = User.objects.create(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

# Summary for phase 1:
    # RegisterSerializer: Creates new users and hashes their password.

    # LoginSerializer: Reads username and password for login.

    # UserSerializer: Returns clean user info in JSON format.
# Then in views.py, we use these serializers to handle registration and login logic.


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ClientAssignmentSerializer(serializers.ModelSerializer):
    lawyer = serializers.StringRelatedField()
    client = serializers.StringRelatedField()

    class Meta:
        model = ClientAssignment
        fields = ['id', 'lawyer', 'client', 'status', 'created_at']


class CreateAssignmentSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()

    def validate_client_id(self, value):
        from .models import User, ClientAssignment

        try:
            client = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Client does not exist")

        # Ensure the target user is actually a client
        if client.role != "individual":
            raise serializers.ValidationError("Only clients can be assigned")

        # Ensure client does not already have a lawyer
        if hasattr(client, "lawyer_assignment"):
            raise serializers.ValidationError("Client already has a lawyer")

        return value