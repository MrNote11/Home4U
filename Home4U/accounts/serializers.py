from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import  UserProfile
from django.contrib.auth import authenticate
import re
from django.contrib.auth.models import User


class UserSerializers(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    # number = serializers.CharField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'confirm_password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    
    def validate_number(self, value):
        """Validate phone number format"""
        phone_pattern = r'^\+?1?\d{9,15}$'  # Validates phone numbers like +123456789 or 123456789
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Invalid phone number format.")
        return value
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)  # Remove confirm_password before saving
        user = User.objects.create_user(**validated_data)  # Automatically hashes the password
        return user  # ✅ Return user correctly


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")
        user = authenticate(username=username, password=password)
        if user is None:
            user = authenticate(email=username, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        return {'user': user}

class OTPVerificationSerializers(serializers.Serializer):
    otp = serializers.CharField(max_length=6)

class UpdateSerializers(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    profile_image = serializers.ImageField(required=False)  # Make optional.

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'profile_image']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.profile_image:
            representation['profile_image'] = request.build_absolute_uri(instance.profile_image.url)
        return representation

    def update(self, instance, validated_data):
        user_data = validated_data.get('user')
        if user_data:
            instance.user.username = user_data.get('username', instance.user.username)
            instance.user.email = user_data.get('email', instance.user.email)
            instance.user.save()

        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.save()
        return instance

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6) # 6 digit otp.
    new_password = serializers.CharField(write_only=True)

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate_refresh_token(self, value):
        try:
            RefreshToken(value)
        except Exception:
            raise ValidationError("Invalid refresh token.")
        return value