from django.db import models
from django.contrib.auth import get_user_model
import uuid
from contents.models import ReservationDetails
from contents.models import ReservationContents
from cloudinary.models import CloudinaryField


User = get_user_model()
class Payment(models.Model):
    class Status(models.TextChoices):
        SUCCESSFUL = "SUCCESSFUL", 'Successful',
        FAILED = "FAILED", 'Failed',
        PENDING = "PENDING", 'Pending',
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reservation = models.ForeignKey(ReservationDetails, on_delete=models.CASCADE, related_name="reservations") # ✅ Link to ReservationDetails
    house = models.ForeignKey(ReservationContents, on_delete=models.CASCADE, related_name='housenames')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=13, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)



    def __str__(self):

            return f"Payment {self.reference} - {self.status}"