# Generated by Django 4.2.18 on 2025-04-11 10:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0007_payment_house'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payment',
            name='payload',
        ),
    ]
