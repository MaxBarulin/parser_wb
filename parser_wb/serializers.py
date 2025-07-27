from rest_framework.serializers import ModelSerializer

from parser_wb.models import GoldAppleProduct


class ProductSerializer(ModelSerializer):

    class Meta:
        model = GoldAppleProduct
        fields = "__all__"
