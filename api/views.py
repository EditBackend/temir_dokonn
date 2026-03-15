from datetime import timedelta
from decimal import Decimal
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view,action
from rest_framework.response import Response
from rest_framework import status,viewsets
from django.http import JsonResponse
from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
# from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone



from .models import Product, Sale, Category, Supplier, WarehouseIncome, Customer,Employee,Role,ActivityLog,Batch
from .serializers import (
    ProductSerializer,
    SaleSerializer,
    CategorySerializer,
    SupplierSerializer,
    WarehouseIncomeSerializer,
    CustomerSerializer,
    EmployeeSerializer,
    RoleSerializer,
    BatchSerializer
)


# User = get_user_model()


# class IsBossOnly(permissions.BasePermission):
#     """Faqat boshliq (boss) ko‘ra oladi/sozlay oladi."""
#     def has_permission(self, request, view):
#         return bool(request.user and request.user.is_authenticated and getattr(request.user, "role", None) == "boss")
#

# class EmployeeViewSet(ModelViewSet):
#     """
#     Xodimlar CRUD:
#     - List/Create/Update/Delete -> faqat boss
#     """
#     queryset = User.objects.all().order_by("-id")
#     serializer_class = EmployeeSerializer
#     # permission_classes = [IsBossOnly]



class BatchViewSet(viewsets.ModelViewSet):

    queryset = Batch.objects.all().order_by('-received_date')
    serializer_class = BatchSerializer

    # Sotuvni qayd qilish (qty_left kamayadi)
    @action(detail=True, methods=['post'])
    def sell(self, request, pk=None):

        batch = self.get_object()

        qty = request.data.get('qty')

        if not qty:
            return Response({"error": "qty yuborilmadi"}, status=400)

        qty_sold = Decimal(qty)

        if qty_sold <= 0:
            return Response({"error": "qty 0 dan katta bo'lishi kerak"}, status=400)

        if qty_sold > batch.qty_left:
            return Response(
                {"error": "Sotiladigan miqdor omborda yetarli emas"},
                status=400
            )

        batch.qty_left -= qty_sold
        batch.save()

        return Response({
            "batch_code": batch.batch_code,
            "sold": qty_sold,
            "qty_left": batch.qty_left
        })


    # Dead stock alert (90 kun sotilmagan batchlar)
    @action(detail=False, methods=['get'])
    def alerts(self, request):

        limit_date = timezone.now().date() - timedelta(days=90)

        alert_batches = Batch.objects.filter(
            qty_left__gt=0,
            received_date__lt=limit_date
        )

        serializer = self.get_serializer(alert_batches, many=True)

        return Response(serializer.data)

class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all().order_by("-id")
    serializer_class = CustomerSerializer

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

    @transaction.atomic
    def create(self, request, *args, **kwargs):

        items = request.data.get("lines")
        customer = request.data.get("customer")
        payment_type = request.data.get("payment_type") or None

        if not items:
            return Response({"error": "Items yuborilmadi"}, status=400)

        last_sale = Sale.objects.order_by('-check_number').first()

        new_check_number = (
            last_sale.check_number + 1
            if last_sale and last_sale.check_number
            else 1
        )

        common_time = timezone.now()
        created_sales = []

        for item in items:

            try:
                product = Product.objects.get(id=int(item.get("product")))
            except Product.DoesNotExist:
                return Response({"error": "Mahsulot topilmadi"}, status=404)

            quantity = float(item.get("quantity"))
            price = float(item.get("price"))
            # Xodim arzon sotmasligi uchun tekshiruv
            if price < float(product.price):
                return Response(
                    {"error": f"{product.name} ni {product.price} dan arzon sotib bo‘lmaydi"},
                    status=400
                )
            if product.quantity < quantity:
                return Response(
                    {"error": f"{product.name} omborda yetarli emas"},
                    status=400
                )

            remaining_qty = quantity

            # FIFO batchlarni olish
            batches = Batch.objects.filter(
                product=product,
                qty_left__gt=0
            ).order_by('received_date')

            if batches.exists():

                for batch in batches:

                    if remaining_qty <= 0:
                        break

                    deduct_qty = min(batch.qty_left, remaining_qty)

                    batch.qty_left -= deduct_qty
                    batch.save()

                    sale = Sale.objects.create(
                        product=product,
                        quantity=deduct_qty,
                        price=price,
                        customer=customer,
                        payment_type=payment_type,
                        check_number=new_check_number,
                        created_at=common_time,
                        batch=batch
                    )

                    created_sales.append(sale)

                    remaining_qty -= deduct_qty

            else:

                sale = Sale.objects.create(
                    product=product,
                    quantity=quantity,
                    price=price,
                    customer=customer,
                    payment_type=payment_type,
                    check_number=new_check_number,
                    created_at=common_time
                )

                created_sales.append(sale)

            product.quantity -= quantity
            product.save()

        ActivityLog.objects.create(
            employee_id=request.data.get("employee"),
            action=f"Sotuv amalga oshirdi (chek {new_check_number})"
        )

        serializer = self.get_serializer(created_sales, many=True)

        return Response({
            "check_number": new_check_number,
            "sales": serializer.data
        }, status=201)
# HISOBOT
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

    daily_summary = (
        sales
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(
            total_sales=Sum('total_price'),
            total_quantity=Sum('quantity'),
            total_checks=Sum(1)  #  nechta sotuv (chek emas, sotuvlar soni)
        )
        .order_by('-date')
    )

    grand_total = sales.aggregate(
        total_sum=Sum('total_price'),
        total_quantity=Sum('quantity')
    )

    return Response({
        "sana_from": sana_from,
        "sana_to": sana_to,
        "kunlik_hisobot": daily_summary,
        "umumiy_summa": grand_total
    })

#  Oxirgi chek raqamni olish

@api_view(['GET'])
def last_check_number(request):

    last_sale = Sale.objects.order_by('-check_number').first()

    return Response({
        "last_check_number": last_sale.check_number if last_sale else 0
    })


@api_view(['GET'])
def new_check_number(request):

    last_sale = Sale.objects.order_by('-check_number').first()

    new_check = last_sale.check_number + 1 if last_sale else 1

    return Response({"new_check_number": new_check})



#  CHECK raqam boyicha

@api_view(['GET'])
def check_details(request, check_number=None):
    if check_number is None:

        checks = Sale.objects.values('check_number').distinct().order_by('-check_number')
        result = []

        for check in checks:

            number = check['check_number']
            sales = Sale.objects.filter(check_number=number)

            total = sales.aggregate(total_sum=Sum('total_price'))

            products = []

            for sale in sales:
                products.append({
                    "product": sale.product.name,
                    "quantity": sale.quantity,
                    "price": sale.price,
                    "total": sale.total_price,
                    "payment_type": sale.payment_type
                })

            result.append({
                "check_number": number,
                "customer": sales.first().customer,
                "date": sales.first().created_at,
                "total_sum": total['total_sum'],
                "products": products
            })

        return Response(result)

    sales = Sale.objects.filter(check_number=check_number)

    if not sales.exists():
        return Response({"error": "Chek topilmadi"}, status=404)

    total = sales.aggregate(total_sum=Sum('total_price'))

    products = []

    for sale in sales:
        products.append({
            "product": sale.product.name,
            "quantity": sale.quantity,
            "price": sale.price,
            "total": sale.total_price,
            "payment_type": sale.payment_type
        })

    return Response({
        "check_number": check_number,
        "customer": sales.first().customer,
        "date": sales.first().created_at,
        "total_sum": total['total_sum'],
        "products": products
    })


class SupplierViewSet(ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


#  INCOME CREATE
@csrf_exempt
@api_view(['POST'])
def create_income(request):
    supplier_id = request.data.get("supplier")
    items = request.data.get("lines")

    if not supplier_id:
        return Response({"error": "Supplier bo'sh"}, status=400)

    if not items:
        return Response({"error": "Items bo'sh"}, status=400)

    supplier_id = int(supplier_id)

    last_income = WarehouseIncome.objects.order_by('-check_number').first()
    new_check_number = (
        last_income.check_number + 1
        if last_income and last_income.check_number
        else 1
    )

    common_time = timezone.now()

    with transaction.atomic():

        for item in items:

            try:
                product = Product.objects.get(id=int(item.get("product")))
            except Product.DoesNotExist:
                return Response({"error": "Mahsulot topilmadi"}, status=404)

            quantity = int(item.get("quantity"))
            price = float(item.get("price"))

            total_price = quantity * price   #  QO‘SHILDI — total hisoblash

            WarehouseIncome.objects.create(
                supplier_id=supplier_id,
                product=product,
                quantity=quantity,
                price=price,
                total_price=total_price,   #  QO‘SHILDI — modelga yozildi
                check_number=new_check_number,
                created_at=common_time
            )

            product.quantity += quantity
            product.save()

    return Response({
        "message": "Kirim saqlandi",
        "check_number": new_check_number
    })


    # kirim tarixini yozish
    ActivityLog.objects.create(
    employee_id=request.data.get("employee"),
    action="Omborga kirim qildi"
)


#  INCOME DETAIL
@api_view(['GET'])
def income_check_details(request, check_number=None):

    if check_number is None:

        checks = WarehouseIncome.objects.values('check_number').distinct().order_by('-check_number')
        result = []

        for check in checks:

            number = check['check_number']
            incomes = WarehouseIncome.objects.filter(check_number=number)

            total = incomes.aggregate(total_sum=Sum('quantity'))

            products = []

            for income in incomes:
                products.append({
                    "product": income.product.name,
                    "quantity": income.quantity,
                    "price": income.price
                })

            result.append({
                "check_number": number,
                # "payment_type": payment_type,
                "supplier": incomes.first().supplier.name,
                "date": incomes.first().created_at,
                "total_quantity": total['total_sum'],
                "products": products
            })

        return Response(result)

    incomes = WarehouseIncome.objects.filter(check_number=check_number)

    if not incomes.exists():
        return Response({"error": "Kirim chek topilmadi"}, status=404)

    total = incomes.aggregate(total_sum=Sum('quantity'))

    products = []

    for income in incomes:
        products.append({
            "product": income.product.name,
            "quantity": income.quantity,
            "price": income.price
        })

    return Response({
        "check_number": check_number,
        "supplier": incomes.first().supplier.name,
        "date": incomes.first().created_at,
        "total_quantity": total['total_sum'],
        "products": products
    })



# real foydani hisoblash uchun api
@api_view(['GET'])
def real_profit(request):

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

    total_sales = 0
    total_cost = 0
    total_profit = 0

    for sale in sales:

        if not sale.product:
            continue

        sale_sum = sale.total_price

        # FIFO bo‘yicha kirim narxi
        if sale.batch:
            cost_sum = sale.batch.unit_cost * sale.quantity
        else:
            cost_sum = sale.product.last_price * sale.quantity

        profit = sale_sum - cost_sum

        total_sales += sale_sum
        total_cost += cost_sum
        total_profit += profit

    return Response({
        "total_sales": total_sales,
        "total_cost": total_cost,
        "real_profit": total_profit
    })

# LOGIN qilish uchun api
@api_view(['POST'])
def login_employee(request):

    phone = request.data.get("phone")
    password = request.data.get("password")

    try:
        employee = Employee.objects.get(phone=phone, password=password)
    except Employee.DoesNotExist:
        return Response(
            {"error": "Login yoki parol noto'g'ri"},
            status=400
        )

    return Response({
        "id": employee.id,
        "name": employee.first_name,
        "role": employee.role.name
    })


# EMPLOYEE barcha crud amallari
class EmployeeViewSet(ModelViewSet):
    queryset = Employee.objects.all().order_by("-id")
    serializer_class = EmployeeSerializer


# ROLE uchun crud amallari
class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer




# CASH FLOW (kunlik / oylik pul oqimi)
@api_view(['GET'])
def cash_flow(request):
    sana_from = request.query_params.get('sana_from')
    sana_to = request.query_params.get('sana_to')
    sales = Sale.objects.all()
    incomes = WarehouseIncome.objects.all()
    if sana_from and sana_to:

        sales = sales.filter(
            created_at__date__range=[
                parse_date(sana_from),
                parse_date(sana_to)
            ]
        )
        incomes = incomes.filter(
            created_at__date__range=[
                parse_date(sana_from),
                parse_date(sana_to)
            ]
        )

    # Kirim (sotuvlar)
    total_income = sales.aggregate(
        income=Sum('total_price')
    )['income'] or 0

    # Chiqim (tovar sotib olish)
    total_expense = incomes.aggregate(
        expense=Sum('total_price')
    )['expense'] or 0

    profit = total_income - total_expense

    return Response({
        "kirim": total_income,
        "chiqim": total_expense,
        "foyda": profit
    })