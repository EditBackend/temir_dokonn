from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
# from rest_framework.permissions import IsAuthenticated

from .models import Product, Sale
from .serializers import ProductSerializer, SaleSerializer


def home(request):
    return JsonResponse({"message": "Temir Shop Backend ishlayapti!"})


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer



class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all().order_by('-created_at')
    # 👆 YANGI SOTUVLAR HAR DOIM TEPADA
    serializer_class = SaleSerializer
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Sotish tugmasi bosilganda:
        - Sale yoziladi
        - Product.quantity kamayadi
        """
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

        # Ombordagi miqdorni kamaytirish
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

    # total_income = sales.aggregate(
    #     total=Sum('total_price')
    # )['total'] or 0

    daily_product_sales = (
        sales
        .annotate(date=TruncDate('created_at'))
        .values('date', 'product_id', 'product_name')
        .annotate(
            sold_quantity=Sum('quantity'),
            total_sales=Sum('total_price'),
            price=Sum('total_price') / Sum('quantity')
        )
        .order_by('-date')
        # 👆 hisobotda ham eng yangi sana tepada chiqadi
    )

    return JsonResponse({
        "sana_from": sana_from,
        "sana_to": sana_to,
        # "jami_kirim": total_income,
        "hisobot": list(daily_product_sales)
    })
