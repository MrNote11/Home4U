# Generated by Django 4.2.18 on 2025-04-07 11:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contents', '0008_rename_post_reservationdetails_housing'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservationdetails',
            name='booking',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='reservationdetails',
            name='status',
            field=models.BooleanField(default=False),
        ),
    ]
