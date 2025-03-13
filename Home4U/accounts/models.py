import random
import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class OTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)  # Allow null for flexibility
    purpose = models.CharField(
        max_length=20,
        choices=(('registration', 'Registration'), ('password_reset', 'Password Reset')),
        default='registration'
    )
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return self.expires_at < timezone.now()

    @staticmethod
    def generate_otp():
        return ''.join(random.choices('0123456789', k=6))

    def save(self, *args, **kwargs):
        if not self.otp:
            self.otp = self.generate_otp()
        if not self.expires_at:
            self.expires_at = timezone.now() + datetime.timedelta(minutes=10)
        super().save(*args, **kwargs)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='user_images/', default='user_images/Good_things_are_coming_fOD6Mp2.png')

    def __str__(self):
        return self.user.username