from rest_framework import serializers
from .models import Product, Sale, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class SaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('total_price', 'created_at')
