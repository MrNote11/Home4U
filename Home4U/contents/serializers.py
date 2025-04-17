from datetime import timedelta
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
        
class BookingSerializer(serializers.ModelSerializer):
    
    house = ReservationContentsSerializer()

    class Meta:
        model = ReservationDetails
        fields = ['house']


class PostRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostRating
        fields = ['ratings']

    def validate_ratings(self, value):
        """Check that the rating is between 1 and 5."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
        
        
    



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

    def validate(self, data):
        """Combined validation for check-in/check-out relationship and minimum stay."""
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        
        # Ensure both dates exist
        if not check_in or not check_out:
            raise serializers.ValidationError("Both check-in and check-out dates are required.")
        
        # Ensure check-out is after check-in
        if check_out <= check_in:
            raise serializers.ValidationError("Check-out must be after check-in.")
        
        # Calculate if dates are at least a month apart
        delta = relativedelta(check_out, check_in)
        total_months = delta.years * 12 + delta.months
        days_difference = (check_out - check_in).days
        
        # Check if at least a month apart (either month count >= 1 or days >= 30)
        if total_months < 1 and days_difference < 30:
            raise serializers.ValidationError("Booking must be for at least one month.")
        
        # Add calculated fields
        data['check_in_plus_15'] = check_in + timedelta(days=15)
        data['check_out_plus_15'] = check_out + timedelta(days=15)
        data['total_days'] = days_difference
        
        return data

    def get_total_price(self, obj):
        # Return the calculated total price from the model method.
        return obj.calculate_total_price()
        
    def create(self, validated_data):
        # Extract calculated fields before creating the instance
        validated_data.pop('check_in_plus_15', None)
        validated_data.pop('check_out_plus_15', None)
        validated_data.pop('total_days', None)
        
        # Create the reservation with the remaining data
        instance = super().create(validated_data)
        
        # If you want to store the calculated fields on the model
        # you can do so here (if they exist as model fields)
        # instance.check_in_plus_15 = check_in_plus_15
        # instance.check_out_plus_15 = check_out_plus_15
        # instance.total_days = total_days
        # instance.save()
        
        return instance


    
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
            'guest_first_name', 'guest_last_name', 'guest_phone_number', 'guest_email', 'total_price',
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
        print(f"instance.first_name1: {instance.guest_first_name}")
        instance.guest_first_name = validated_data.get('guest_first_name', instance.guest_first_name)
        print(f"instance.first_name2: {instance.guest_first_name}")
        instance.guest_last_name = validated_data.get('guest_last_name', instance.guest_last_name)
        instance.guest_phone_number = validated_data.get('guest_phone_number', instance.guest_phone_number)
        instance.guest_email = validated_data.get('guest_email', instance.guest_email)
        instance.save()  # ✅ Save changes

        return instance  # ✅ Return the updated instance

    def get_total_price(self, instance):
        # Return the calculated total price from the model method.
        return instance.calculate_total_price()