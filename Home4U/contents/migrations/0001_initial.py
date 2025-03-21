# Generated by Django 4.2.18 on 2025-03-12 13:39

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservationContents',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('house', models.CharField(max_length=50)),
                ('beds', models.IntegerField(blank=True, choices=[(1, '1 Bed'), (2, '2 Beds'), (3, '3 Beds'), (4, '4 Beds'), (5, '5 Beds'), (11, '11 Beds')], null=True)),
                ('slug', models.SlugField(blank=True, editable=False, null=True)),
                ('address', models.CharField(blank=True, max_length=50)),
                ('wifi', models.BooleanField(blank=True, choices=[(True, 'Wifi Available'), (False, 'Wifi Not Available')], null=True)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('country', models.CharField(blank=True, max_length=50)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('swimmingpool', models.BooleanField(blank=True, choices=[(True, 'Yes'), (False, 'No')], null=True)),
                ('status', models.CharField(blank=True, max_length=50)),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('likes', models.ManyToManyField(blank=True, related_name='liked_reservations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ReservationImages',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_url', models.ImageField(blank=True, default='default.jpg', upload_to='reservation_images/')),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='contents.reservationcontents')),
            ],
        ),
        migrations.CreateModel(
            name='ReservationDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=30, null=True)),
                ('last_name', models.CharField(max_length=30, null=True)),
                ('phone_number', models.CharField(max_length=30, null=True)),
                ('email', models.EmailField(max_length=254, null=True)),
                ('guests', models.IntegerField(blank=True, choices=[(1, '1 Guest'), (2, '2 Guests'), (3, '3 Guests'), (4, '4 Guests'), (5, '5 Guests')], null=True)),
                ('check_in', models.DateField(blank=True, null=True)),
                ('check_out', models.DateField(blank=True, null=True)),
                ('post', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='contents.reservationcontents')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PostRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('ratings', models.PositiveSmallIntegerField(null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='contents.reservationcontents')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
