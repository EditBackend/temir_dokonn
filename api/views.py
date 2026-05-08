from datetime import timedelta
from decimal import Decimal
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view,action
from rest_framework.response import Response
from rest_framework import status,viewsets
from django.http import JsonResponse
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek, TruncDate
from django.utils.dateparse import parse_date
# from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.views import APIView
from .serializers import ExpenseCategorySerializer
from .utils import send_telegram_message
import statistics
from collections import defaultdict
from decimal import Decimal
from rest_framework.permissions import AllowAny
from datetime import datetime
from dateutil.relativedelta import relativedelta



from .models import Product, Sale, Category, Supplier, WarehouseIncome, Customer, Employee, Role, ActivityLog, Batch, \
    Expense, SaleItem, ExpenseCategory, Payment, SaleItem, Product, Unit, PaymentType
from .serializers import (
    ExpenseCreateSerializer,
    ProductSerializer,
    SaleSerializer,
    CategorySerializer,
    SupplierSerializer,
    WarehouseIncomeSerializer,
    CustomerSerializer,
    EmployeeSerializer,
    RoleSerializer,
    BatchSerializer, ExpenseSerializer, ExpenseCreateSerializer,
    UnitSerializer
)
class RoleDetailView(APIView):
    # GET va DELETE metodlari o'zgarishsiz qoladi...

    def put(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
            serializer = RoleSerializer(role, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"success": True, "data": serializer.data})
            return Response(serializer.errors, status=400)
        except Role.DoesNotExist:
            return Response({"success": False}, status=404)

    # MANA SHU QISMNI QO'SHING
    def patch(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
            # partial=True — bu PATCH uchun eng muhim joyi (qisman yangilashga ruxsat beradi)
            serializer = RoleSerializer(role, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"success": True, "data": serializer.data})
            return Response(serializer.errors, status=400)
        except Role.DoesNotExist:
            return Response({"success": False}, status=404)
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


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

#abc analiz
@api_view(['GET'])
def abc_xyz_analysis_optimized(request):
    weeks_count = 12
    end_date = timezone.now()
    # start_date ni haftaning boshiga to'g'rilaymiz
    start_date = (end_date - timedelta(weeks=weeks_count)).replace(hour=0, minute=0, second=0, microsecond=0)
    RECOMMENDATIONS = {
        "AX": "Asosiy kassa generatori. Doimiy zaxira talab etiladi.",
        "AY": "Mavsumiy kassa generatori. Zaxirani mavsumga qarab rejalashtiring.",
        "AZ": "Yuqori foyda, kutilmagan talab.Buyurtma asosida ishlash tavsiya etiladi.",
        "BX": "Barqaror o'rtacha foyda. Zaxirani me'yorda ushlab turing.",
        "BY": "O'rtacha va o'zgaruvchan talab. Aksiyalar orqali sotuvni oshirish mumkin.",
        "BZ": "Kutilmagan talab va o'rtacha foyda. Katta zaxira qilmang.",
        "CX": "Kam foyda, barqaror sotuv. Logistikani optimallashtiring.",
        "CY": "Kam foyda va o'zgaruvchan talab. Doimiy nazorat shart emas.",
        "CZ": "O'lik kapital. Assortimentdan chiqarish tavsiya etiladi."
    }

    # Sotuvlarni olish
    sales_qs = (
        SaleItem.objects
        .filter(sale__created_at__range=[start_date, end_date])
        .annotate(week=TruncWeek('sale__created_at'))  # Haftaning boshiga (dushanba) o'giradi
        .values('product_id', 'product__name', 'product__quantity', 'product__last_price', 'week')
        .annotate(
            weekly_revenue=Sum(F('price') * F('quantity')),
            weekly_profit=Sum((F('price') - F('product__last_price')) * F('quantity'))
        )
    )
    product_data = defaultdict(lambda: {
        "name": "", "weekly_sales": {}, "total_revenue": 0, "total_profit": 0, "stock": 0
    })

    #Ma'lumotlarni yig'ish
    for entry in sales_qs:
        p_id = entry['product_id']
        # Haftani string ko'rinishida saqlaymiz, solishtirish oson bo'lishi uchun
        w_str = entry['week'].strftime('%Y-%W')
        product_data[p_id]["name"] = entry['product__name']
        product_data[p_id]["stock"] = float(entry['product__quantity'] or 0)
        product_data[p_id]["total_revenue"] += float(entry['weekly_revenue'] or 0)
        product_data[p_id]["total_profit"] += float(entry['weekly_profit'] or 0)
        product_data[p_id]["weekly_sales"][w_str] = float(entry['weekly_revenue'] or 0)

    total_revenue_sum = sum(p["total_revenue"] for p in product_data.values())
    if total_revenue_sum == 0:
        return Response({"success": True, "message": "Sotuvlar topilmadi", "data": {}})

    # ABC va XYZ hisoblash
    sorted_products = sorted(product_data.items(), key=lambda x: x[1]['total_revenue'], reverse=True)
    # Barcha mavjud haftalar ro'yxatini tuzamiz
    all_weeks = []
    curr = start_date
    while curr <= end_date:
        all_weeks.append(curr.strftime('%Y-%W'))
        curr += timedelta(weeks=1)
    result = []
    cumulative_percent = 0
    xyz_counts = {"X": 0, "Y": 0, "Z": 0}
    category_counts = {"A": 0, "B": 0, "C": 0}
    for p_id, p_info in sorted_products:
        revenue = p_info['total_revenue']
        #ABC analiz
        percent = (revenue / total_revenue_sum) * 100
        cumulative_percent += percent
        abc = 'A' if cumulative_percent <= 80 else ('B' if cumulative_percent <= 95 else 'C')
        category_counts[abc] += 1

        # XYZ  aanaliz
        sales_values = [p_info["weekly_sales"].get(w, 0) for w in all_weeks]
        variation = 1.0
        if len(sales_values) > 1:
            mean = sum(sales_values) / len(sales_values)
            if mean > 0:
                std_dev = statistics.stdev(sales_values)
                variation = std_dev / mean

        xyz = 'X' if variation <= 0.15 else ('Y' if variation <= 0.3 else 'Z')
        xyz_counts[xyz] += 1
        item_class = f"{abc}{xyz}"
        result.append({
            "product": p_info["name"],
            "toifa": item_class,
            "ombor": p_info["stock"],
            "aylanma": round(revenue, 2),
            "sof_foyda": round(p_info["total_profit"], 2),
            "abc": abc,
            "xyz": xyz,
            "recommendation": RECOMMENDATIONS.get(item_class, "")
        })

    return Response({
        "success": True,
        "data": {
            "total_revenue": round(total_revenue_sum, 2),
            "summary": {"abc": category_counts, "xyz": xyz_counts},
            "items": result
        }
    })

class ExpenseAnalyticsView(APIView):
    def get(self, request):
        data = (
            Expense.objects
            .filter(is_deleted=False)
            .values('category__name')
            .annotate(total=Sum('amount'))
        )

        return Response({
            "success": True,
            "data": list(data)
        })

class TopProductsView(APIView):
    def get(self, request):
        qs = (
            SaleItem.objects
            .values('product__name')
            .annotate(total=Sum(F('price') * F('quantity')))
            .order_by('-total')[:5]
        )

        return Response({
            "success": True,
            "data": list(qs)
        })


class ProductsTableView(APIView):
    def get(self, request):
        # Sale modelidan guruhlab olish
        qs = (
            Sale.objects.values('product__name')
            .annotate(
                total_sales=Sum('total_price'),
                total_quantity=Sum('quantity')
            )
            .order_by('-total_sales')
        )

        result = []
        for item in qs:
            total = item['total_sales'] or 0
            qty = item['total_quantity'] or 0
            result.append({
                "name": item['product__name'],
                "total_sales": total,
                "quantity": qty,
                "avg_price": round(total / qty, 2) if qty else 0
            })
        return Response({"success": True, "data": result})


@api_view(['GET'])
def top_products(request):
    # Bu yerda ham Sale modeliga o'tamiz
    data = (
        Sale.objects.values('product__name')
        .annotate(total=Sum('total_price'))
        .order_by('-total')[:10]
    )
    return Response({
        "success": True,
        "data": [{"product": i['product__name'], "total": i['total']} for i in data]
    })

class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.filter(is_deleted=False)

    def get_serializer_class(self):
        return ExpenseCreateSerializer

#boshliq uchun expences oynasi
class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.filter(is_deleted=False).select_related('category', 'created_by')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        date_from = params.get('date_from')
        date_to = params.get('date_to')
        category_id = params.get('category_id')
        branch_id = params.get('branch_id')
        search = params.get('search')

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = qs.filter(note__icontains=search)
        return qs

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response({"success": True})


class ExpenseCategoryList(APIView):
    permission_classes = [AllowAny] # Mana bu joy xatoni to'g'rilaydi

    def get(self, request):
        data = ExpenseCategory.objects.all()
        serializer = ExpenseCategorySerializer(data, many=True)
        return Response({"success": True, "data": serializer.data})

    def post(self, request):
        serializer = ExpenseCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data}, status=201)
        return Response({"success": False, "errors": serializer.errors}, status=400)
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
    return JsonResponse({"message": "Temir dokon Backendda muammo yo'q.Chunki Backendchi yaxshi bola!"})


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

            # item.get dan kelgan qiymatni Decimal ga o'giramiz
            quantity = Decimal(str(item.get("quantity", 0)))
            price = Decimal(str(item.get("price", 0)))
            # Xodim arzon sotmasligi uchun tekshiruv
            # if price < float(product.price):
            #     return Response(
            #         {"error": f"{product.name} ni {product.price} dan arzon sotib bo‘lmaydi"},
            #         status=400
            #     )
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
                        customer_id=customer,  # <--- 'customer' emas, 'customer_id' qildik
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
                    customer_id=customer,  # <--- 'customer' emas, 'customer_id' qildik
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

        # TELEGRAMGA YUBORISH
        message = f"🛒 YANGI SAVDO!\n\n🧾 Chek: {new_check_number}\n\n"
        total_sum = 0
        for sale in created_sales:
            total = float(sale.price) * float(sale.quantity)
            total_sum += total
            message += f"📦 {sale.product.name}\n"
            message += f"⚖️ {sale.quantity} x {sale.price} = {total}\n\n"
        message += f"💰 Jami: {total_sum} so'm"
        send_telegram_message(message)


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




@api_view(['GET'])
def check_details(request, check_number=None):

    if check_number is None:
        checks = Sale.objects.values('check_number').distinct().order_by('-check_number')
        result = []

        for check in checks:
            number = check['check_number']
            sales = Sale.objects.filter(check_number=number)

            total = sales.aggregate(total_sum=Sum('total_price'))

            first_sale = sales.first()  # ✅ bir marta olamiz

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
                "customer": CustomerSerializer(first_sale.customer).data,  # ✅ FIX
                "date": first_sale.created_at,
                "total_sum": total['total_sum'],
                "products": products
            })

        return Response(result)

    # Bitta check uchun
    sales = Sale.objects.filter(check_number=check_number)

    if not sales.exists():
        return Response({"error": "Chek topilmadi"}, status=404)

    total = sales.aggregate(total_sum=Sum('total_price'))
    first_sale = sales.first()  # ✅

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
        "customer": CustomerSerializer(first_sale.customer).data,  # ✅ FIX
        "date": first_sale.created_at,
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

# CASH FLOW TREND (chart uchun)
@api_view(['GET'])
def cash_flow_trend(request):

    sana_from = request.GET.get('sana_from')
    sana_to = request.GET.get('sana_to')

    sales = Sale.objects.all()
    incomes = WarehouseIncome.objects.all()

    if sana_from and sana_to:
        sales = sales.filter(created_at__date__range=[sana_from, sana_to])
        incomes = incomes.filter(created_at__date__range=[sana_from, sana_to])

    sales_data = sales.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_in=Sum('total_price')
    ).order_by('date')

    expense_data = incomes.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_out=Sum('total_price')
    ).order_by('date')

    return Response({
        "sales": sales_data,
        "expenses": expense_data
    })


# CASH FLOW DAILY TABLE
@api_view(['GET'])
def cash_flow_daily(request):

    sales = Sale.objects.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_in=Sum('total_price')
    )

    incomes = WarehouseIncome.objects.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total_out=Sum('total_price')
    )

    return Response({
        "sales": sales,
        "expenses": incomes
    })


# CATEGORY BREAKDOWN
@api_view(['GET'])
def expense_categories(request):


    data = WarehouseIncome.objects.values(
        'product__category__name'
    ).annotate(
        total=Sum('total_price')
    )

    return Response(data)





@api_view(['GET'])
def top_products(request):
    data = (
        Sale.objects
        .values('product__name')
        .annotate(total=Sum('total_price'))
        .order_by('-total')[:5]
    )

    result = [
        {
            "product": item["product__name"],
            "total": item["total"]
        }
        for item in data
    ]

    return Response(result)



@api_view(['GET'])
def monthly_summary(request):

    month = request.GET.get('month')  # 2026-03

    sales = Sale.objects.all()
    incomes = WarehouseIncome.objects.all()

    if month:
        sales = sales.filter(created_at__startswith=month)
        incomes = incomes.filter(created_at__startswith=month)

    total_sales = sales.aggregate(total=Sum('total_price'))['total'] or 0
    total_expense = incomes.aggregate(total=Sum('total_price'))['total'] or 0

    net = total_sales - total_expense

    return Response({
        "sales": total_sales,
        "expenses": total_expense,
        "net": net,
        "growth_percent": 0  # keyin qo‘shamiz
    })


@api_view(['GET'])
def monthly_trend(request):

    sales = Sale.objects.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        sales=Sum('total_price')
    )

    expenses = WarehouseIncome.objects.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        expenses=Sum('total_price')
    )

    return Response({
        "sales": sales,
        "expenses": expenses
    })


@api_view(['GET'])
def monthly_comparison(request):

    current_month = request.GET.get('month')  # 2026-03

    # oldingi oy
    year, m = map(int, current_month.split('-'))
    prev_month = f"{year}-{m-1:02d}"

    current_sales = Sale.objects.filter(
        created_at__startswith=current_month
    ).aggregate(total=Sum('total_price'))['total'] or 0

    prev_sales = Sale.objects.filter(
        created_at__startswith=prev_month
    ).aggregate(total=Sum('total_price'))['total'] or 0

    return Response({
        "current": current_sales,
        "previous": prev_sales
    })


@api_view(['GET'])
def best_worst_day(request):

    data = Sale.objects.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total_price')
    )

    best = max(data, key=lambda x: x['total'], default=None)
    worst = min(data, key=lambda x: x['total'], default=None)

    return Response({
        "best_day": best,
        "worst_day": worst
    })

@api_view(['GET'])
def activity_list(request):
    logs = ActivityLog.objects.order_by('-created_at')[:10]

    result = [
        {
            "text": log.action,
            "time": log.created_at
        }
        for log in logs
    ]

    return Response(result)

#
# @api_view(['GET'])
# def dashboard(request):
#     sana_from = request.GET.get('sana_from')
#     sana_to = request.GET.get('sana_to')
#
#     # ===== CASH FLOW =====
#     sales = Sale.objects.all()
#     incomes = WarehouseIncome.objects.all()
#
#     if sana_from and sana_to:
#         sales = sales.filter(created_at__date__range=[sana_from, sana_to])
#         incomes = incomes.filter(created_at__date__range=[sana_from, sana_to])
#
#     total_income = sales.aggregate(total=Sum('total_price'))['total'] or 0
#     total_expense = incomes.aggregate(total=Sum('total_price'))['total'] or 0
#     profit = total_income - total_expense
#
#     # ===== TREND =====
#     sales_trend = sales.annotate(
#         date=TruncDate('created_at')
#     ).values('date').annotate(
#         total=Sum('total_price')
#     ).order_by('date')
#
#     expenses_trend = incomes.annotate(
#         date=TruncDate('created_at')
#     ).values('date').annotate(
#         total=Sum('total_price')
#     ).order_by('date')
#
#     # ===== CATEGORY =====
#     categories = WarehouseIncome.objects.values(
#         'product__category__name'
#     ).annotate(
#         total=Sum('total_price')
#     )
#
#     # ===== RESPONSE =====
#     return Response({
#         "summary": {
#             "kirim": total_income,
#             "chiqim": total_expense,
#             "foyda": profit
#         },
#         "trend": {
#             "sales": sales_trend,
#             "expenses": expenses_trend
#         },
#         "categories": categories
#     })





class DashboardViewSet(viewsets.ViewSet):
    # Ruxsatni shu yerning o'zida hamma metodlar uchun ochib qo'yamiz
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        sana_from = request.GET.get('date_from')
        sana_to = request.GET.get('date_to')
        p_type_id = request.GET.get('payment_type')

        sales = Sale.objects.all()
        warehouse_incomes = WarehouseIncome.objects.all()
        other_expenses = Expense.objects.filter(is_deleted=False)

        if sana_from and sana_to:
            sales = sales.filter(created_at__date__range=[sana_from, sana_to])
            warehouse_incomes = warehouse_incomes.filter(created_at__date__range=[sana_from, sana_to])
            other_expenses = other_expenses.filter(date__range=[sana_from, sana_to])

        if p_type_id:
            sales = sales.filter(payment_type_id=p_type_id)

        total_sales = sales.aggregate(total=Sum('total_price'))['total'] or 0
        total_warehouse_cost = warehouse_incomes.aggregate(total=Sum('total_price'))['total'] or 0
        total_other_cost = other_expenses.aggregate(total=Sum('amount'))['total'] or 0
        total_expense = total_warehouse_cost + total_other_cost

        # --- O'tgan oy bilan taqqoslash (Yangi qism) ---
        prev_month_sales = 0
        growth_percent = 0
        if sana_from and sana_to:
            try:
                # Stringni sanaga o'tkazamiz
                d1 = datetime.strptime(sana_from, '%Y-%m-%d')
                d2 = datetime.strptime(sana_to, '%Y-%m-%d')
                # Bir oy oldingi sanani hisoblaymiz
                p_sana_from = d1 - relativedelta(months=1)
                p_sana_to = d2 - relativedelta(months=1)

                prev_sales_qs = Sale.objects.filter(created_at__date__range=[p_sana_from, p_sana_to])
                prev_month_sales = prev_sales_qs.aggregate(total=Sum('total_price'))['total'] or 0

                if prev_month_sales > 0:
                    growth_percent = ((total_sales - prev_month_sales) / prev_month_sales) * 100
            except Exception as e:
                print(f"Sana hisoblashda xato: {e}")

        return Response({
            "success": True,
            "data": {
                "total_sales": total_sales,
                "total_expenses": total_expense,
                "warehouse_cost": total_warehouse_cost,
                "other_cost": total_other_cost,
                "net_cash": total_sales - total_expense,
                "comparison": {
                    "prev_month_sales": prev_month_sales,
                    "growth_percent": round(growth_percent, 2)
                }
            }
        })

    @action(detail=False, methods=['get'], url_path='payment-types')
    def payment_types(self, request):
        types = PaymentType.objects.all()
        return Response({
            "success": True,
            "data": [{"id": t.id, "name": t.name} for t in types]
        })    @action(detail=False, methods=['get'], url_path='payment-types')

    def payment_types(self, request):
        # To'lov turlari bo'yicha dinamik filtr
        sales = Sale.objects.all()
        types = PaymentType.objects.all()
        data = []
        for p_type in types:
            amount = sales.filter(payment_type=p_type).aggregate(total=Sum('total_price'))['total'] or 0
            data.append({
                "type": p_type.name,
                "amount": amount
            })

        return Response({
            "success": True,
            "data": data
        })
    @action(detail=False, methods=['get'], url_path='top-products')
    def top_products(self, request):
        # 1. Filtrlarni olish
        sana_from = request.GET.get('date_from')
        sana_to = request.GET.get('date_to')
        limit = request.GET.get('limit')  # Frontendchi xohlagancha limit qo'yishi mumkin
        # 2. Asosiy queryset (Sale emas, balki SaleItem dan foydalanish aniqroq natija beradi)
        # Chunki bir nechta mahsulot bitta sotuvda (Sale) bo'lishi mumkin
        items = SaleItem.objects.all()
        # 3. Sana bo'yicha filtrlash
        if sana_from and sana_to:
            items = items.filter(sale__created_at__date__range=[sana_from, sana_to])
        # 4. Guruhlash va hisoblash
        data = (
            items.values('product__id', 'product__name')
            .annotate(
                revenue=Sum(F('price') * F('quantity')),  # Haqiqiy tushum
                qty=Sum('quantity')  # Sotilgan miqdor
            )
            .order_by('-revenue')  # Eng ko'p pul olib kelganidan boshlab
        )
        # 5. Limit qo'llash
        if limit:
            data = data[:int(limit)]
        else:
            # Agar limit yuborilmasa, odatda 10-20 ta mahsulot yetarli
            data = data[:20]
        return Response({
            "success": True,
            "data": [
                {
                    "product_id": i['product__id'],
                    "product_name": i['product__name'],
                    "revenue": round(i['revenue'], 2),
                    "qty": i['qty']
                } for i in data
            ]
        })

#Kredeti analitikalari
@api_view(['GET'])
def credit_summary(request):
    # faqat nasiya sotuvlar
    credits = Sale.objects.filter(payment_type='Nasiya')
    total_credit = credits.aggregate(total=Sum('total_price'))['total'] or 0
    # 30 kundan oshganini overdue qilamiz
    overdue_date = timezone.now() - timedelta(days=30)
    overdue_credit = credits.filter(
        created_at__lt=overdue_date
    ).aggregate(total=Sum('total_price'))['total'] or 0
    collected_amount = Payment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0
    # riskli mijoz (overdue borlar)
    risky_customers = Customer.objects.filter(
        sale__payment_type='Nasiya',
        sale__created_at__lt=overdue_date
    ).distinct().count()

    return Response({
        "success": True,
        "data": {
            "total_credit": total_credit,
            "overdue_credit": overdue_credit,
            "collected_amount": collected_amount,
            "risky_customers": risky_customers
        }
    })





@api_view(['GET'])
def credit_aging(request):
    today = timezone.now()
    credits = Sale.objects.filter(payment_type='Nasiya')
    buckets = {
        "0-30": 0,
        "31-60": 0,
        "61-90": 0,
        "90+": 0
    }
    for sale in credits:
        days = (today - sale.created_at).days
        if days <= 30:
            buckets["0-30"] += sale.total_price
        elif days <= 60:
            buckets["31-60"] += sale.total_price
        elif days <= 90:
            buckets["61-90"] += sale.total_price
        else:
            buckets["90+"] += sale.total_price
    return Response({
        "success": True,
        "data": [
            {"bucket": k, "amount": v}
            for k, v in buckets.items()
        ]
    })



from .utils import update_customer_score, calculate_credit_limit

@api_view(['GET'])
def debtors_list(request):
    customers = Customer.objects.all()
    result = []
    for c in customers:
        update_customer_score(c)  # ballni yangilaymiz
        sales = Sale.objects.filter(customer=c, payment_type='Nasiya')
        total_credit = sales.aggregate(total=Sum('total_price'))['total'] or 0
        if total_credit > 0:
            credit_limit = calculate_credit_limit(c)

            result.append({
                "customer_id": c.id,
                "name": f"{c.first_name} {c.last_name}",
                "score": c.score,  #  yangi
                "total_credit": total_credit,
                "credit_limit": credit_limit,  #  yangi
                "status": (
                    "danger" if c.score <= 3 else
                    "warning" if c.score <= 6 else
                    "good"
                )
            })

    return Response(result)


@api_view(['GET'])
def recent_payments(request):
    payments = Payment.objects.order_by('-date')[:10]
    return Response({
        "success": True,
        "data": [
            {
                "payment_id": p.id,
                "customer_name": str(p.customer),
                "amount": p.amount,
                "date": p.date
            }
            for p in payments
        ]
    })



@api_view(['GET'])
def debtor_detail(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Mijoz topilmadi"}, status=404)
    # faqat nasiya savdolar
    sales = Sale.objects.filter(customer=customer, payment_type='Nasiya')
    total_credit = sales.aggregate(total=Sum('total_price'))['total'] or 0
    overdue_date = timezone.now() - timedelta(days=30)
    overdue_credit = sales.filter(
        created_at__lt=overdue_date
    ).aggregate(total=Sum('total_price'))['total'] or 0
    # oxirgi savdolar (5 ta)
    recent_sales = sales.order_by('-created_at')[:5]
    # oxirgi to‘lovlar (5 ta)
    recent_payments = Payment.objects.filter(
        customer=customer
    ).order_by('-date')[:5]
    return Response({
        "success": True,
        "data": {
            "customer": {
                "id": customer.id,
                "name": f"{customer.first_name} {customer.last_name}",
                "phone": customer.phone
            },
            "total_credit": total_credit,
            "overdue_credit": overdue_credit,
            "recent_sales": [
                {
                    "id": s.id,
                    "amount": s.total_price,
                    "date": s.created_at
                }
                for s in recent_sales
            ],
            "recent_payments": [
                {
                    "id": p.id,
                    "amount": p.amount,
                    "date": p.date
                }
                for p in recent_payments
            ]
        }
    })