from django.urls import path

from parser_wb.apps import ParserWbConfig
from parser_wb.views import ProductListAPIView, ProductListView

app_name = ParserWbConfig.name

urlpatterns = [
    path('', ProductListView.as_view(), name='products-list'),
    path('api/products/', ProductListAPIView.as_view(), name='products-api-list'),
]
