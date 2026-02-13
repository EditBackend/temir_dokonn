from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date

from .models import Product, Sale, Category
from .serializers import (
    ProductSerializer,
    SaleSerializer,
    CategorySerializer
)


def home(request):
    return JsonResponse({"message": "Temir dokon Backend ishlayapti!"})


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()
        category_id = self.request.query_params.get("category")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset


class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity'))
        price = float(request.data.get('price'))

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": "Mahsulot topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        sale = Sale.objects.create(
            product=product,
            quantity=quantity,
            price=price,
            customer=request.data.get('customer')
        )

        product.quantity -= quantity
        product.save()

        serializer = self.get_serializer(sale)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def sales_summary(request):
    sana_from = request.query_params.get('sana_from')
    sana_to = request.query_params.get('sana_to')

    sales = Sale.objects.all()

    if sana_from and sana_to:
        sales = sales.filter(
            created_at__date__range=[
                parse_date(sana_from),
                parse_date(sana_to)
            ]
        )

    daily_product_sales = (
        sales
        .annotate(date=TruncDate('created_at'))
        .values(
            'created_at',
            'product_id',
            'quantity',
            'price',
            'customer',
            product_name=F('product__name'),
        )
        .annotate(
            total_sales=Sum('total_price'),
            total_price=Sum('total_price') / Sum('quantity')
        )
        .order_by('-date')
    )

    return JsonResponse({
        "sana_from": sana_from,
        "sana_to": sana_to,
        "hisobot": list(daily_product_sales)
    })
