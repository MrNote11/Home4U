from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=UserProfile)
def save_user_profile(sender, instance, **kwargs):
    instance.user.save()

# @receiver(post_save, sender=UserProfile)
# def update_custom_user_profile_image(sender, instance, created, **kwargs):
#     """
#     Signal handler to update the profile_image of the CustomUser whenever the UserProfile is updated.
#     """
#     if instance.user:  # Ensure the UserProfile is linked to a User
#         user = instance.user

#         # Check if the profile_image has changed in the UserProfile
#         if instance.profile_image and instance.profile_image != instance.user.userprofile.profile_image:
#             # Update the profile image in the UserProfile (not directly in the User)
#             instance.user.userprofile.profile_image = instance.profile_image
#             instance.user.userprofile.save()  # Save the updated UserProfile
