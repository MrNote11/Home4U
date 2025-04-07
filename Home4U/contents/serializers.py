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
        # Ensure check-in date is not in the past.
        if value < timezone.now().date():
            raise serializers.ValidationError("Check-in date cannot be in the past.")
        return value

    def validate_check_out(self, value):
        # Ensure check-out date is in the future.
        if value <= timezone.now().date():
            raise serializers.ValidationError("Check-out date must be in the future.")
        return value

    def validate(self, attrs):
        # Object-level validation to ensure check-out is after check-in.
        check_in = attrs.get('check_in')
        check_out = attrs.get('check_out')
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError("Check-out must be after check-in.")
        return attrs

    def get_total_price(self, obj):
        # Return the calculated total price from the model method.
        return obj.calculate_total_price()



    
class ReservationDetailSerializer(serializers.ModelSerializer):
    """Handles reservation details and ensures user validation"""
    
    customer_first_name = serializers.CharField(write_only=True)
    customer_last_name = serializers.CharField(write_only=True)
    customer_email = serializers.EmailField(write_only=True)
    customer_phone_number = serializers.CharField(write_only=True)
    total_price = serializers.SerializerMethodField()
    # days = serializers.CharField(read_only=True)

    class Meta:
        model = ReservationDetails
        fields = (
            'first_name', 'last_name', 'phone_number', 'email', 'total_price',
            'customer_first_name', 'customer_last_name', 'customer_email', 'customer_phone_number'
        )
    
    # def get_total_price(self, obj):
    #     print(f"obj: {obj}")
    #     """Retrieve the calculated total price."""
    #     return obj.calculate_total_price()    
  
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
        
        data.pop('customer_first_name', None)
        data.pop('customer_last_name', None)
        data.pop('customer_email', None)
        data.pop('customer_phone_number', None)

        return data



    def update(self, instance, validated_data):
        """Update reservation details"""
        print(f"validated_data: {validated_data}")
        print(f"instance: {instance}")
        print(f"instance.first_name1: {instance.first_name}")
        instance.first_name = validated_data.get('first_name', instance.first_name)
        print(f"instance.first_name2: {instance.first_name}")
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.email = validated_data.get('email', instance.email)
        instance.save()  # ✅ Save changes

        return instance  # ✅ Return the updated instance

    def get_total_price(self, instance):
        # Return the calculated total price from the model method.
        return instance.calculate_total_price()