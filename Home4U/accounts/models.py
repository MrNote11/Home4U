import random
import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from cloudinary.models import CloudinaryField
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import random
from django_resized import ResizedImageField


# Model
class VerificationToken(models.Model):
    class Choices(models.TextChoices):
        REGISTRATION = "RG", 'Registration' 
        PASSWORD_RESET = "PR", 'Password_Reset'
        
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)  # Unique token
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)  # Expiry time
    purpose = models.CharField(
        max_length=20,
        choices=Choices.choices
    )
    is_used = models.BooleanField(default=False)
    otp = models.IntegerField(
        validators=[
            MinValueValidator(1000, message="OTP must be 4 digits."),
            MaxValueValidator(9999, message="OTP must be 4 digits.")
        ],
        blank=True, 
        null=True
    )

    def is_expired(self):
        return self.expires_at < timezone.now()

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = random.randint(1000, 9999)
            
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=11)  # 11 min expiration
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Verification Token"
        verbose_name_plural = "Verification Tokens"
        ordering = ['-created_at']
        # Add index for faster lookups
        indexes = [
            models.Index(fields=['user', 'purpose', 'is_used']),
            models.Index(fields=['otp']),
        ]    
        
    def __str__(self):
        return f"{self.user}-{self.token}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='user_images/', default='media/user_images/Good_things_are_coming.png')

    def __str__(self):
        return self.user.username