# Generated by Django 4.2.18 on 2025-03-28 11:14

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_verificationtoken_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='profile_image',
            field=cloudinary.models.CloudinaryField(default='user_images/Good_things_are_coming_fOD6Mp2.png', max_length=255, verbose_name='user_images/'),
        ),
    ]
