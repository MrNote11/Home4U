import django_filters
from .models import ReservationContents
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter, NumberFilter, DateTimeFilter, BooleanFilter, ChoiceFilter
from django.db.models import Q, Count, Avg
from rest_framework.pagination import PageNumberPagination


class ReservationFilter(django_filters.FilterSet):

    class Meta:
        model = ReservationContents
        fields = {'house':
            ['iexact', 'icontains'],
            'state':['iexact', 'icontains']} # make sure to reference the correct field in 'Housedb'

