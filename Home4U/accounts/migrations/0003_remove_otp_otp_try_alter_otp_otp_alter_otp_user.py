# Generated by Django 4.2.18 on 2025-03-07 01:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0002_otp_is_used_otp_otp_try_alter_otp_otp'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='otp',
            name='otp_try',
        ),
        migrations.AlterField(
            model_name='otp',
            name='otp',
            field=models.CharField(max_length=4),
        ),
        migrations.AlterField(
            model_name='otp',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
