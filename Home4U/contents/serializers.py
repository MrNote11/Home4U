from rest_framework import serializers
from .models import (ReservationContents, ReservationImages,
                     PostRating, ReservationDetails,
                     PostLike)
from django.utils import timezone
import re
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta  # ✅ Import for month difference
from payments.models import Payment

class ReservationImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationImages
        fields = ['image_url']



    

        # Create the reservation
        # return ReservationDetails.objects.create(user=user, post=post, **validated_data)

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
    
    
class ReservationDetailSerializer(serializers.ModelSerializer):
    """Handles reservation details and ensures user validation"""

    customer_first_name = serializers.CharField(write_only=True)
    customer_last_name = serializers.CharField(write_only=True)
    customer_email = serializers.EmailField(write_only=True)
    customer_phone_number = serializers.CharField(write_only=True)

    class Meta:
        model = ReservationDetails
        fields = (
            'first_name', 'last_name', 'phone_number', 'email',
            'customer_first_name', 'customer_last_name', 'customer_email', 'customer_phone_number'
        )

    def validate(self, data):
        """Ensure customer details match the logged-in user"""
        user = self.context.get('user')

        if not user:
            raise serializers.ValidationError("User is not authenticated.")

        errors = {}

        if data.get("customer_first_name") != user.first_name:
            errors["customer_first_name"] = "Does not match the logged-in user."

        if data.get("customer_last_name") != user.last_name:
            errors["customer_last_name"] = "Does not match the logged-in user."

        if data.get("customer_email") != user.email:
            errors["customer_email"] = "Does not match the logged-in user."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        """Create a reservation entry"""

        user = self.context.get('user')
        post_id = self.context.get('post')

        # Extract customer details and remove them from validated_data
        customer_first_name = validated_data.pop('customer_first_name', None)
        customer_last_name = validated_data.pop('customer_last_name', None)
        customer_email = validated_data.pop('customer_email', None)
        customer_phone_number = validated_data.pop('customer_phone_number', None)

        # Ensure post exists
        try:
            post = ReservationContents.objects.get(id=post_id)
        except ReservationContents.DoesNotExist:
            raise serializers.ValidationError("Invalid post ID provided.")

        # Create reservation
        reservation = ReservationDetails.objects.create(
            user=user, post=post, **validated_data
        )

        return reservation

    def update(self, instance, validated_data):
        """Update reservation details"""

        user = self.context.get('user')
        post_id = self.context.get('post')

        if not isinstance(post_id, int):
            raise serializers.ValidationError("Invalid post ID. Expected an integer.")

        # Extract and discard customer details
        validated_data.pop('customer_first_name', None)
        validated_data.pop('customer_last_name', None)
        validated_data.pop('customer_email', None)
        validated_data.pop('customer_phone_number', None)

        try:
            post = ReservationContents.objects.get(id=post_id)
        except ReservationContents.DoesNotExist:
            raise serializers.ValidationError("Invalid post ID provided.")

        # ✅ Update instance fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.email = validated_data.get('email', instance.email)
        instance.post = post  # ✅ Ensure reservation is linked to the correct post
        instance.save()  # ✅ Save changes

        return instance  # ✅ Return the updated instance

    
    
    # def create(self, validated_data):
    #     """Creates a reservation entry"""
    #     user = self.context.get('user')
    #     post = self.context.get('post')
        
        
    #     if not post:
    #         raise serializers.ValidationError("Post is required.")
        
    #     customer_details = {
    #     "customer_first_name": validated_data.pop('customer_first_name', user.first_name),
    #     "customer_last_name": validated_data.pop('customer_last_name', user.last_name),
    #     "customer_email": validated_data.pop('customer_email', user.email),
    #     "customer_phone_number": validated_data.pop('customer_phone_number', getattr(user, 'phone_number', None))
    #     }
        
    #     reservation = ReservationDetails.objects.create(user=user, post=post, **validated_data)

    #     reservation.customer_details = customer_details  # Attach for reference

    #     return reservation
            