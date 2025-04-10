# Generated by Django 4.2.18 on 2025-04-11 10:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contents', '0013_alter_reservationdetails_house'),
        ('payments', '0008_remove_payment_payload'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='reservation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='contents.reservationdetails'),
        ),
    ]
