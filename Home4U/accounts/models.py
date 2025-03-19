import random
import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid




class VerificationToken(models.Model):
    class Choices(models.TextChoices):
        REGISTERATION = "RG", 'Registration',
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

    def is_expired(self):
        return self.expires_at < timezone.now()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)  # 10 min expiration
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.user}-{self.token}"    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='user_images/', default='user_images/Good_things_are_coming_fOD6Mp2.png')

    def __str__(self):
        return self.user.username