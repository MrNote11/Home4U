from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import  UserProfile
from django.contrib.auth import authenticate
import re
from django.contrib.auth.models import User


User = get_user_model()

class UserSerializers(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)  # Non-unique by default
    last_name = serializers.CharField(required=True)   # Non-unique by default
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
  
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'confirm_password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_password(self, value):
        # Check if password starts with uppercase
        if not  len(value) > 9:
            raise serializers.ValidationError("Password is too short or long... ")
        
        if len(value) < 8:
            raise serializers.ValidationError("almost their")
        
        if not value[0].isupper():
            raise serializers.ValidationError("Password must start with an uppercase letter and continue in lowercase.")
        
        if len(value) > 1 and not value[1].islower():
             raise serializers.ValidationError("The second character of the password must be lowercase.")
         
        # Check for at least one digit
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        
        if len(value) > 1 and value[1].isalpha() and not value[1].islower():
            raise serializers.ValidationError("The second character of the password (if a letter) must be lowercase.")

        # Check for at least one symbol
        symbols = re.compile(r'[!@#$%^&*(),.?":{}|<>]')
        if not symbols.search(value):
            raise serializers.ValidationError("Password must contain at least one symbol.")
        
        # Check that it contains alphanumeric characters
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Password must contain at least one letter.")
        
        return value
    
    def validate(self, data):
        # Check that passwords match
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
    
    def create(self, validated_data):
        # Remove confirm_password from validated data
        validated_data.pop('confirm_password', None)
        # Create user
        user = User.objects.create_user(**validated_data)
        return user
    
    

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")
        user = authenticate(username=username, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        return {'user': user}



class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()



class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.IntegerField(
        min_value=1000,
        max_value=9999,
        error_messages={
            'min_value': 'OTP must be 4 digits.',
            'max_value': 'OTP must be 4 digits.'
        }
    )
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, data):
        """
        Check that the two password entries match
        """
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Password fields didn't match."})
        return data
    
    
    
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


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate_refresh_token(self, value):
        try:
            RefreshToken(value)
        except Exception:
            raise ValidationError("Invalid refresh token.")
        return value
    
    
class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if user.is_active:
                raise serializers.ValidationError("User is already active.")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")    