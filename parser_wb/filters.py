import django_filters

from parser_wb.models import Product


class ProductFilter(django_filters.FilterSet):
    """Добавил фильтры для API (min|max - price, rating, feedbacks)"""

    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    min_feedbacks = django_filters.NumberFilter(field_name='feedbacks', lookup_expr='gte')
    max_feedbacks = django_filters.NumberFilter(field_name='feedbacks', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['min_price', 'max_price', 'min_rating', 'max_rating', 'min_feedbacks', 'max_feedbacks']
