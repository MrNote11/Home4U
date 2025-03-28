from rest_framework import serializers
from .models import (ReservationContents, ReservationImages,
                     PostRating, ReservationDetails,
                     PostLike)
from django.utils import timezone
import re
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta  # ✅ Import for month difference


class ReservationImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationImages
        fields = ['image_url']



class ReservationDetailSerializer(serializers.ModelSerializer):
    """Handles reservation details and ensures user validation"""
    customer_first_name = serializers.CharField(write_only=True)  # Accept user input
    customer_last_name = serializers.CharField(write_only=True)
    customer_email = serializers.EmailField(write_only=True)
    customer_phone_number = serializers.CharField(write_only=True)

    class Meta:
        model = ReservationDetails
        fields = (
            'first_name', 'last_name', 'phone_number', 'email','check_in', 'check_out',
            'customer_first_name', 'customer_last_name', 'customer_email', 'customer_phone_number'
        )

    def get_customer_first_name(self, obj):
        return self.context['user'].first_name if self.context.get('user') else None

    def get_customer_last_name(self, obj):
        return self.context['user'].last_name if self.context.get('user') else None

    def get_customer_email(self, obj):
        return self.context['user'].email if self.context.get('user') else None

    def get_customer_phone_number(self, obj):
        """Get the logged-in user's phone number if available"""
        user = self.context.get('user')
        return getattr(user, 'profile', {}).get('phone_number', None) or getattr(user, 'phone_number', None) if user else None

    def validate(self, data):
        """Ensure the provided customer details match the logged-in user"""
        user = self.context.get('user')

        if not user:
            raise serializers.ValidationError("User is not authenticated.")

        errors = {}

        if data.get("customer_first_name") and data["customer_first_name"] != user.first_name:
            errors["customer_first_name"] = "Does not match the logged-in user."

        if data.get("customer_last_name") and data["customer_last_name"] != user.last_name:
            errors["customer_last_name"] = "Does not match the logged-in user."

        if data.get("customer_email") and data["customer_email"] != user.email:
            errors["customer_email"] = "Does not match the logged-in user."

        # user_phone = getattr(user, "profile", {}).get("phone_number", None) or getattr(user, "phone_number", None)
        # if data.get("customer_phone_number") and data["customer_phone_number"] != user_phone:
        #     errors["customer_phone_number"] = "Does not match the logged-in user."

        if errors:
            raise serializers.ValidationError(errors)  # 🚨 Stop processing if incorrect

        return data


    def create(self, validated_data):
        """Creates a reservation entry"""
        user = self.context.get('user')
        post = self.context.get('post')

        if not post:
            raise serializers.ValidationError("Post is required.")
        
        # validated_data.pop('customer_first_name', None)
        # validated_data.pop('customer_last_name', None)
        # validated_data.pop('customer_email', None)
        # validated_data.pop('customer_phone_number', None)

        # Create the reservation
        return ReservationDetails.objects.create(user=user, post=post, **validated_data)

class ReservationContentsSerializer(serializers.ModelSerializer):
    likes_count = serializers.SerializerMethodField()
    images = ReservationImagesSerializer(many=True) 
    # ratings_counts = serializers.SerializerMethodField()
    ratings_reviews = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ReservationContents
        fields = ['id', 'house', 'beds', 'price', 'address', 'state', 'swimmingpool',
                  'wifi','ratings_reviews', 'country', 
                  'images', 'average_rating',
                  'likes_count', 'description', 'status']  

    def get_likes_count(self, obj):
        return PostLike.objects.filter(post=obj).count() 

    
    def get_ratings_reviews(self, obj):
        # Count the number of distinct users who have rated the current post
        return PostRating.objects.filter(post=obj).values('user').distinct().count()
    
    def get_ratings_counts(self, obj):
        user = self.context.get('user')
        user_ratings = PostRating.objects.filter(user=user, post=obj)

        if user_ratings.exists():
            # Sum of ratings for the current user for this post
            ratings_sum = user_ratings.aggregate(Sum('ratings'))['ratings__sum']
            # Return the sum of ratings instead of dividing by 2
            return ratings_sum
        return 0



class PostLikeSerializer(serializers.ModelSerializer):
    post = ReservationContentsSerializer()

    class Meta:
        model = PostLike
        fields = ['id', 'post', 'created_at']


class GuestsSerializers(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = ReservationDetails
        fields = ['check_in', 'check_out', 'guests', 'total_price']

    def validate_check_in(self, value):
        """Ensure check-in is not in the past."""
        if value < timezone.now().date():
            raise serializers.ValidationError("Check-in date cannot be in the past.")
        return value

    def validate_check_out(self, value):
        """Ensure check-out is after check-in."""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Check-out date must be in the future.")
        return value

    def validate(self, attrs):
        """Ensure check-out is after check-in."""
        check_in = attrs.get('check_in')
        check_out = attrs.get('check_out')

        if check_out and check_in and check_out <= check_in:
            raise serializers.ValidationError("Check-out must be after check-in.")
        return attrs

    def get_total_price(self, obj):
        """Retrieve the calculated total price."""
        return obj.calculate_total_price()

    def create(self, validated_data):
        """Create a reservation with the correct post ID."""
        user = self.context.get('user')
        post_id = self.context.get('post')

        if not post_id:
            raise serializers.ValidationError("Post ID is required.")

        try:
            post = ReservationContents.objects.get(id=post_id)
        except ReservationContents.DoesNotExist:
            raise serializers.ValidationError("Invalid post ID provided.")

        return ReservationDetails.objects.create(user=user, post=post, **validated_data)