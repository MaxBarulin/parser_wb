import django_filters
from .models import GoldAppleProduct


class ProductFilter(django_filters.FilterSet):
    """Фильтры для API (min|max - price, rating) для модели GoldAppleProduct."""

    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')

    class Meta:
        model = GoldAppleProduct
        fields = ['min_price', 'max_price', 'min_rating', 'max_rating']
