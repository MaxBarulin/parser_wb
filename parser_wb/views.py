from django.views.generic import ListView
from rest_framework.generics import ListAPIView

from parser_wb.filters import ProductFilter
from parser_wb.models import GoldAppleProduct
from parser_wb.serializers import ProductSerializer


class ProductListAPIView(ListAPIView):
    """Api для запроса списка товаров и их фильтрации."""
    queryset = GoldAppleProduct.objects.all()  # <--- ИЗМЕНЕНИЕ 2: Используем правильный queryset
    serializer_class = ProductSerializer
    filterset_class = ProductFilter


class ProductListView(ListView):
    model = GoldAppleProduct  # <--- ИЗМЕНЕНИЕ 3: Используем правильную модель
    template_name = 'parser_wb/product_list.html'
    context_object_name = 'products'

