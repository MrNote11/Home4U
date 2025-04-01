from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from dateutil.relativedelta import relativedelta
from cloudinary.models import CloudinaryField
from django_resized import ResizedImageField

class ReservationContents(models.Model):

        BEDS = [

        (1, '1 Bed'),

        (2, '2 Beds'),

        (3, '3 Beds'),

        (4, '4 Beds'),

        (5, '5 Beds'),

        (11, '11 Beds')

        ]



        SWIMMINGPOOL = [

        (True, 'Yes'),

        (False, 'No')

        ]



        WIFI = [

        (True, 'Wifi Available'),

        (False, 'Wifi Not Available')

        ]



        house = models.CharField(max_length=50)

        beds = models.IntegerField(choices=BEDS, blank=True, null=True)

        slug = models.SlugField(blank=True, null=True, editable=False)

        address = models.CharField(max_length=50, blank=True)

        wifi = models.BooleanField(choices=WIFI, blank=True, null=True)

        state = models.CharField(max_length=100, blank=True)

        country = models.CharField(max_length=50, editable=True, blank=True)

        price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

        swimmingpool = models.BooleanField(choices=SWIMMINGPOOL, blank=True, null=True)

        status = models.CharField(max_length=50, blank=True)

        description = models.TextField(blank=True)

        created = models.DateTimeField(auto_now_add=True)



        def __str__(self):

            return f"House: {self.house}, Location: {self.state}, {self.country}"








class ReservationDetails(models.Model):

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True)

    post = models.ForeignKey(ReservationContents, on_delete=models.CASCADE, null=True)

    first_name = models.CharField(max_length=30, null=True)

    last_name = models.CharField(max_length=30, null=True)

    phone_number = models.CharField(max_length=30, null=True)

    email = models.EmailField(null=True)

    GUESTS = [

    (1, '1 Guest'),

    (2, '2 Guests'),

    (3, '3 Guests'),

    (4, '4 Guests'),

    (5, '5 Guests'),

    ]

    guests = models.IntegerField(choices=GUESTS, blank=True, null=True)

    check_in = models.DateField(blank=True, null=True)

    check_out = models.DateField(blank=True, null=True)



    def calculate_total_price(self):

        """Calculate the total price based on months stayed and post price."""
        if self.check_in and self.check_out and self.post:
                print(f"Check-in: {self.check_in}, Check-out: {self.check_out}")
                delta = relativedelta(self.check_out, self.check_in)
                num_months = delta.years * 12 + delta.months
                remaining_days = (self.check_out - self.check_in).days - (num_months * 30)
        
                # If remaining days exceed half a month, count it as a full month
                if remaining_days > 15:
                    num_months += 2
                print(f"Number of months: {num_months}")
                print(f"Post price: {self.post.price}")
                total_price = num_months * self.post.price 
                print(f"Total price: {total_price}")
                return total_price
        
class ReservationImages(models.Model):
        reservation = models.ForeignKey(ReservationContents, on_delete=models.CASCADE, related_name='images')
        image_url = ResizedImageField(size=[600, 600],upload_to='reservation_images/', quality= 85,default='default.jpg', blank=True)

        def __str__(self):
            return f"Image {self.id} for Reservation {self.reservation.id}"



class PostRating(models.Model):
    post = models.ForeignKey(ReservationContents, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    ratings = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5)),
        null=True
    )
    
    # class Meta:
    #     unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user} - {self.ratings} for apartment: {self.post}"

class PostLike(models.Model):
    post = models.ForeignKey(ReservationContents, on_delete=models.CASCADE, related_name='post_likes')
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='user_likes')
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('post', 'user')  # Ensure a user can only like a post once

    def __str__(self):
        return f"{self.user.username} likes {self.post.house}"