from datetime import timedelta
from decimal import Decimal
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view,action
from rest_framework.response import Response
from rest_framework import status,viewsets
from django.http import JsonResponse
from django.db.models import Sum, F
from django.db.models.functions import TruncWeek, TruncDate, TruncHour
from django.utils.dateparse import parse_date
# from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.views import APIView
from .serializers import ExpenseCategorySerializer
from .utils import send_telegram_message
import statistics
import uuid
from collections import defaultdict
from decimal import Decimal
from rest_framework.permissions import AllowAny
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rest_framework import generics

from .models import Product, Sale, Category, Supplier, WarehouseIncome, Customer, Employee, Role, ActivityLog, Batch, \
    Expense, SaleItem, ExpenseCategory, Payment, SaleItem, Product, Unit, PaymentType,ArchivedItem,CustomerPayment
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


@api_view(['POST'])
def receive_customer_payment(request, customer_id):
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return Response({"success": False, "error": "Mijoz topilmadi"}, status=status.HTTP_404_NOT_FOUND)

    # 1. Ma'lumotlarni olish (JSON yoki Form-Data bo'lsa ham muammosiz o'qiydi)
    amount_str = request.data.get('amount')
    payment_type = request.data.get('payment_type', 'cash')

    if not amount_str:
        return Response({"success": False, "error": "Summa kiritilmadi (amount field majburiy)"},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        payment_amount = Decimal(str(amount_str).replace(',', ''))  # Agar frontend vergul bilan yuborsa ham tozalaydi
        if payment_amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return Response({"success": False, "error": "Noto'g'ri summa formati kiritildi"},
                        status=status.HTTP_400_BAD_REQUEST)

    # 2. Matematika: Qarzni kamaytirish
    if customer.total_debt >= payment_amount:
        customer.total_debt -= payment_amount
    else:
        customer.total_debt = Decimal('0.00')

    if customer.debt >= payment_amount:
        customer.debt -= payment_amount
    else:
        customer.debt = Decimal('0.00')

    customer.save()

    # 3. To'lovlar tarixiga saqlash (related_name muammosi yechilgan)
    CustomerPayment.objects.create(
        customer=customer,
        amount=payment_amount,
        payment_type=payment_type
    )

    # 4 ActivityLog qismini XAVFSIZ qilish:
    # 500 xatolik bermasligi uchun try-except ichiga olamiz (agar modelda boshqa required fieldlar bo'lsa)
    try:
        from .models import ActivityLog
        # Agar modelingizda employee yoki user majburiy bo'lsa, xato bermasligi uchun qidirib ko'ramiz
        ActivityLog.objects.create(
            action=f"Mijoz {customer.name} {payment_amount} so'm qarzini uzdi. To'lov turi: {payment_type}"
        )
    except Exception as log_error:
        print(f"Log yozishda xato bo'ldi, lekin qarz o'chdi: {log_error}")
        # Log yaratishda xato bo'lsa ham mijozning puli kuyib ketmasligi uchun jarayonni to'xtatmaymiz

    return Response({
        "success": True,
        "message": "To'lov muvaffaqiyatli qabul qilindi",
        "new_total_debt": customer.total_debt,
        "new_debt": customer.debt
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def customer_profile_details(request, customer_id):
    """
    Mijoz profilidagi barcha ma'lumotlarni bitta joyda berish API
    """
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return Response({"success": False, "error": "Mijoz topilmadi"}, status=404)

    # To'lovlar tarixini olamiz
    payments = customer.customer_debt_payments.all().order_by('-created_at')
    payments_data = [
        {
            "id": p.id,
            "amount": p.amount,
            "payment_type": p.get_payment_type_display(),
            "date": p.created_at.strftime("%Y-%m-%d %H:%M")
        } for p in payments
    ]

    # Xaridlar tarixini olamiz (Agar sizda Sale modelida mijoz bog'langan bo'lsa)
    # Eslatma: Sale modelida customer fieldi bo'lishi kerak
    from .models import Sale
    sales = Sale.objects.filter(customer=customer).order_by('-created_at')
    sales_data = [
        {
            "id": s.id,
            "product": s.product.name if s.product else "O'chirilgan mahsulot",
            "quantity": s.quantity,
            "total_price": s.total_price,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M")
        } for s in sales
    ]

    return Response({
        "success": True,
        "profile": {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "address": customer.address or "Kiritilmagan",
            "last_debt": customer.debt,          # Oxirgi tranzaksiya qarzi
            "total_debt": customer.total_debt,    # Umumiy balans (Yig'ilgan qarz)
        },
        "purchases": sales_data,                  # Xaridlar oynasi uchun
        "payments": payments_data                 # To'lovlar oynasi uchun
    })







@api_view(['GET'])
def archive_list(request):
    archives = ArchivedItem.objects.order_by('-deleted_at')
    data = [
        {
            "tur": item.get_item_type_display(), # 'Ta'minotchi' deb o'zbekcha chiqadi
            "nomi": item.name,
            "sana": item.deleted_at.strftime("%Y-%m-%d %H:%M"),
            "status": item.status
        }
        for item in archives
    ]
    return Response(data)


# EMPLOYEE DETAIL (GET, PATCH, DELETE uchun)
class EmployeeDetailView(APIView):
    permission_classes = [AllowAny]
    def get_object(self, pk):
        try:
            return Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return None
    def get(self, request, pk):
        employee = self.get_object(pk)
        if not employee: return Response(status=404)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)
    def patch(self, request, pk):
        employee = self.get_object(pk)
        if not employee: return Response(status=404)
        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        from .models import ArchivedItem, Employee  #  Employee modelingiz nomini aniq yozing
        from django.shortcuts import get_object_or_404
        employee = get_object_or_404(Employee, pk=pk)
        # Xodim ismi 'name', 'first_name' yoki 'username' bo'lishi mumkin
        emp_name = getattr(employee, 'name',getattr(employee, 'first_name', getattr(employee, 'username', str(employee))))
        ArchivedItem.objects.create(
            item_type='employee',
            name=emp_name,
            original_id=employee.id,
            status="O'chirilgan"
        )
        employee.delete()
        return Response({"success": True, "message": "Xodim arxivlandi"}, status=200)


class RoleDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
            serializer = RoleSerializer(role)
            return Response({"success": True, "data": serializer.data})
        except Role.DoesNotExist:
            return Response({"success": False}, status=404)

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

    def patch(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
            serializer = RoleSerializer(role, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"success": True, "data": serializer.data})
            return Response(serializer.errors, status=400)
        except Role.DoesNotExist:
            return Response({"success": False}, status=404)

    #  Ikkita delete birlashtirildi, avval arxivga saqlaydi, keyin o'chiradi
    def delete(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)

            # 1. Object delete qilinishidan oldin Archive modelga save qilinadi
            ArchivedItem.objects.create(
                item_type='role',
                name=role.name,
                original_id=role.id,
                status="O'chirilgan"
            )

            # 2. Keyin object delete qilinadi
            role.delete()

            return Response({
                "success": True,
                "message": "Rol muvaffaqiyatli o'chirildi va arxivlandi"
            }, status=status.HTTP_200_OK)

        except Role.DoesNotExist:
            return Response({
                "success": False,
                "error": "Rol topilmadi"
            }, status=status.HTTP_404_NOT_FOUND)
class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from .models import ArchivedItem
        from django.db.models.deletion import ProtectedError

        obj_name = getattr(instance, 'name', getattr(instance, 'title', str(instance)))

        try:
            ArchivedItem.objects.create(
                item_type='measure',  # models.py dagi ITEM_TYPES ga 'measure' deb qo'shib qo'ysangiz ham bo'ladi
                name=obj_name,
                original_id=instance.id,
                status="O'chirilgan"
            )
            instance.delete()
            return Response({"success": True, "message": "O'lchov o'chirildi va arxivlandi"}, status=200)

        except ProtectedError:
            return Response({
                "success": False,
                "error": "Bu o'lchov birligiga bog'langan mahsulotlar bor! Uni o'chirish taqiqlangan."
            }, status=400)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)
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
    for entry in sales_qs:
        p_id = entry['product_id']
        w_str = entry['week'].strftime('%Y-%W')
        product_data[p_id]["name"] = entry['product__name']
        product_data[p_id]["stock"] = float(entry['product__quantity'] or 0)
        product_data[p_id]["total_revenue"] += float(entry['weekly_revenue'] or 0)
        product_data[p_id]["total_profit"] += float(entry['weekly_profit'] or 0)
        product_data[p_id]["weekly_sales"][w_str] = float(entry['weekly_revenue'] or 0)

    total_revenue_sum = sum(p["total_revenue"] for p in product_data.values())
    if total_revenue_sum == 0:
        return Response({"success": True, "message": "Sotuvlar topilmadi", "data": {}})

    sorted_products = sorted(product_data.items(), key=lambda x: x[1]['total_revenue'], reverse=True)
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
        percent = (revenue / total_revenue_sum) * 100
        cumulative_percent += percent
        abc = 'A' if cumulative_percent <= 80 else ('B' if cumulative_percent <= 95 else 'C')
        category_counts[abc] += 1
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


# @api_view(['GET'])
# def top_products(request):
#     # Bu yerda ham Sale modeliga o'tamiz
#     data = (
#         Sale.objects.values('product__name')
#         .annotate(total=Sum('total_price'))
#         .order_by('-total')[:10]
#     )
#     return Response({
#         "success": True,
#         "data": [{"product": i['product__name'], "total": i['total']} for i in data]
#     })



#boshliq uchun expences oynasi
class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.filter(is_deleted=False).select_related('category', 'created_by')

    def get_serializer_class(self):
        # Create paytida CreateSerializer, ko'rish paytida oddiy Serializer
        if self.action in ['create', 'update', 'partial_update']:
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def perform_create(self, serializer):
        # Saqlash paytida xodimni avtomatik biriktirish
        serializer.save(created_by=self.request.user)

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


class ExpenseCategoryList(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        if 'pk' in self.kwargs:
            return ExpenseCategory.objects.filter(id=self.kwargs['pk'])
        return ExpenseCategory.objects.all()
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"success": True, "data": response.data}, status=201)

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from .models import ArchivedItem
        # Mijoz ismi modelda 'name', 'full_name' yoki 'first_name' bo'lishi mumkin
        obj_name = getattr(instance, 'name',getattr(instance, 'full_name', getattr(instance, 'first_name', str(instance))))
        ArchivedItem.objects.create(
            item_type='customer',
            name=obj_name,
            original_id=instance.id,
            status="O'chirilgan"
        )
        instance.delete()
        return Response({"success": True, "message": "Mijoz arxivlandi"}, status=200)


def home(request):
    return JsonResponse({"message": "Temir dokon Backendda muammo yo'q.Chunki Backendchi yaxshi bola!"})


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from .models import ArchivedItem

        # Model maydonini xavfsiz aniqlab olish
        obj_name = getattr(instance, 'name', getattr(instance, 'title', str(instance)))

        try:
            # 1. O'chishdan oldin arxiv modeliga yozamiz
            ArchivedItem.objects.create(
                item_type='category',
                name=obj_name,
                original_id=instance.id,
                status="O'chirilgan"
            )

            # 2. Standart DRF o'chirish funksiyasini chaqiramiz (Bu avtomat 204 qaytaradi)
            return super().destroy(request, *args, **kwargs)

        except ProtectedError:
            return Response({
                "success": False,
                "error": "Bu kategoriyaga bog'liq mahsulotlar bor! Avval o'sha mahsulotlarni o'chiring."
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()
        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    #  TUZATILGAN VA SUG'URTALANGAN DESTROY METODI
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from .models import ArchivedItem

        obj_name = getattr(instance, 'name', getattr(instance, 'title', str(instance)))

        try:
            # Tranzaksiya ochamiz agar o'chirish o'xshasa, arxiv ham bazada qoladi. O'xshamasab, ikkalasi ham bekor bo'ladi.
            with transaction.atomic():
                # 1. Arxivga yozamiz
                ArchivedItem.objects.create(
                    item_type='product',
                    name=obj_name,
                    original_id=instance.id,
                    status="O'chirilgan"
                )
                #Standart DRF o'chirish metodini chaqiramiz (Bu avtomat 204 No Content qaytaradi)
                return super().destroy(request, *args, **kwargs)

        except ProtectedError:
            # Agar mahsulot savdoda qatnashgan bo'lsa, frontendga chiroyli ogohlantirish beramiz
            return Response({
                "success": False,
                "error": "Bu mahsulot savdo cheklari (sotuvlar) yoki ombor kirimlariga bog'langan! Shuning uchun uni o'chirib bo'lmaydi."
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
                    SaleItem.objects.create(sale=sale, product=product, quantity=deduct_qty, price=price)
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
                SaleItem.objects.create(sale=sale, product=product, quantity=quantity, price=price)
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
            first_sale = sales.first()

            products = []
            for sale in sales:
                # 👇 XAVFSIZLIK: Agar mahsulot o'chib ketgan bo'lsa xato bermaydi
                product_name = sale.product.name if sale.product else "O'chirilgan mahsulot"

                products.append({
                    "product": product_name,
                    "quantity": sale.quantity,
                    "price": sale.price,
                    "total": sale.total_price,
                    "payment_type": sale.payment_type.name if hasattr(sale.payment_type, 'name') else str(
                        sale.payment_type)
                })

            # XAVFSIZLIK: Mijoz o'chib ketgan bo'lsa ham xato bermasligi uchun tekshiruv
            customer_data = CustomerSerializer(first_sale.customer).data if first_sale.customer else {
                "name": "O'chirilgan mijoz"}

            result.append({
                "check_number": number,
                "customer": customer_data,
                "date": first_sale.created_at if first_sale else None,
                "total_sum": total['total_sum'] or 0,
                "products": products
            })

        return Response(result)

    # Bitta chek ma'lumotlarini olish qismi
    sales = Sale.objects.filter(check_number=check_number)

    if not sales.exists():
        return Response({"error": "Chek topilmadi"}, status=404)

    total = sales.aggregate(total_sum=Sum('total_price'))
    first_sale = sales.first()

    products = []
    for sale in sales:
        #  XAVFSIZLIK: Bu yerda ham mahsulot o'chgan bo'lsa xavfsiz nom beriladi
        product_name = sale.product.name if sale.product else "O'chirilgan mahsulot"

        products.append({
            "product": product_name,
            "quantity": sale.quantity,
            "price": sale.price,
            "total": sale.total_price,
            "payment_type": sale.payment_type.name if hasattr(sale.payment_type, 'name') else str(sale.payment_type)
        })

    # XAVFSIZLIK: Mijoz uchun tekshiruv
    customer_data = CustomerSerializer(first_sale.customer).data if first_sale.customer else {
        "name": "O'chirilgan mijoz"}

    return Response({
        "check_number": check_number,
        "customer": customer_data,
        "date": first_sale.created_at if first_sale else None,
        "total_sum": total['total_sum'] or 0,
        "products": products
    })


class SupplierViewSet(ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

    # KLAS ICHIDA: destroy metodini xavfsiz override qilamiz
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Ismini xavfsiz olish (name yoki kompaniya nomi bo'lsa ham)
        obj_name = getattr(instance, 'name', getattr(instance, 'company_name', str(instance)))

        try:
            # Atomik tranzaksiya: agar o'chsa arxivda qoladi, o'chmasa hammasi bekor bo'ladi
            with transaction.atomic():
                # 1. Object o'chishidan oldin arxivlanadi
                ArchivedItem.objects.create(
                    item_type='supplier',
                    name=obj_name,
                    original_id=instance.id,
                    status="O'chirilgan"
                )

                # 2. Standart yo'l bilan o'chiriladi (Frontend kutgan 204 statusini qaytaradi)
                return super().destroy(request, *args, **kwargs)

        except ProtectedError:
            # Agar ta'minotchi qayergadir bog'langan bo'lsa, xato bermay tushuntiradi
            return Response({
                "success": False,
                "error": "Bu ta'minotchiga bog'langan mahsulotlar yoki kirim hujjatlari bor! Shuning uchun uni o'chirish taqiqlanadi."
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            #  INCOME CREATE & GET PAYMENT TYPEs



@csrf_exempt
@api_view(['GET', 'POST'])
def create_income(request):
    #  1. Agar frontendchi dropdown uchun to'lov turlarini so'rasa:
    if request.method == 'GET':
        types = PaymentType.objects.all()
        data = [{"id": t.id, "name": t.name} for t in types]
        return Response(data)

    #  2. Agar frontendchi kirimni saqlash uchun POST so'rov yuborsa:
    if request.method == 'POST':
        supplier_id = request.data.get("supplier")
        items = request.data.get("lines")
        employee_id = request.data.get("employee")
        # Frontendchi xohlagan 'payment_type' nomini ham, 'payment_type_id' nomini ham tekshirib olamiz:
        payment_type_id = request.data.get("payment_type") or request.data.get("payment_type_id")

        if not supplier_id:
            return Response({"error": "Supplier bo'sh"}, status=400)
        if not items:
            return Response({"error": "Items bo'sh"}, status=400)
        if not payment_type_id:
            return Response({"error": "To'lov turi (payment_type_id) tanlanmagan"}, status=400)
        supplier_id = int(supplier_id)
        try:
            payment_type = PaymentType.objects.get(id=int(payment_type_id))
        except (PaymentType.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Bunday to'lov turi topilmadi"}, status=400)
        p_type_name = payment_type.name.lower()
        chek_umumiy_summasi = Decimal('0.00')
        with transaction.atomic():
            last_income = WarehouseIncome.objects.select_for_update().order_by('-check_number').first()
            new_check_number = (last_income.check_number + 1) if last_income and last_income.check_number else 1
            common_time = timezone.now()
            # Birinchi ta'minotchini blocklab olamiz (Parallel yozishda muammo bo'lmasligi uchun)
            from .models import Supplier
            try:
                supplier = Supplier.objects.select_for_update().get(id=supplier_id)
            except Supplier.DoesNotExist:
                return Response({"error": "Ta'minotchi topilmadi"}, status=404)
            for item in items:
                try:
                    product = Product.objects.select_for_update().get(id=int(item.get("product")))
                except (Product.DoesNotExist, TypeError, ValueError):
                    return Response({"error": f"Mahsulot (ID: {item.get('product')}) topilmadi"}, status=404)
                quantity = Decimal(str(item.get("quantity", 0)))
                price = Decimal(str(item.get("price", 0)))
                total_price = quantity * price

                # Jami chek summasini yig'ib boramiz
                chek_umumiy_summasi += total_price

                # 1. Kirimni yaratish (payment_type bilan birga)
                WarehouseIncome.objects.create(
                    supplier=supplier,
                    product=product,
                    quantity=quantity,
                    price=price,
                    total_price=total_price,
                    check_number=new_check_number,
                    created_at=common_time,
                    payment_type=payment_type,
                    employee_id=employee_id if employee_id else None
                )

                # 2. Batch (Partiya) yaratish
                Batch.objects.create(
                    product=product,
                    supplier=supplier,
                    received_date=common_time.date(),
                    unit_cost=price,
                    qty_in=quantity,
                    qty_left=quantity,
                    batch_code=f"BATCH-{uuid.uuid4().hex[:8].upper()}"
                )

                # 3. Mahsulotni yangilash
                product.refresh_from_db()
                product.last_price = price
                if not product.supplier_id:
                    product.supplier_id = supplier_id
                product.save()
# =================================================================
#  PULLARNI HISOBLASH MANTIQLARI (MUTLAQ XAVFSIZ VARIANT)
# =================================================================
    if 'nasiya' in p_type_name:
        # 1. Oxirgi qarz - joriy chek summasi
        supplier.debt = chek_umumiy_summasi
        supplier.save()  # Avval buni saqlaymiz

        # 2. Jami qarzni xavfsiz hisoblash:
        # Ta'minotchining bazadagi barcha 'Nasiya' bo'lgan kirimlarini qaytadan hisoblab chiqamiz.
        # Shunda frontend 2 marta so'rov yuborgan taqdirda ham, faqat bazadagi bor cheklar yig'indisi chiqadi.


         # Diqqat: 'payment_type__name__icontains' orqali Nasiya kirimlarini filtrlaymiz
        total_nasiya = WarehouseIncome.objects.filter(
            supplier=supplier,
            payment_type__name__icontains='nasiya'
        ).aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')

        # Jami qarzni bazadan hisoblangan aniq summaga tenglashtiramiz (+= EMAS, = ISHLATAMIZ!)
        supplier.total_debt = total_nasiya
        supplier.save()

    # B) Naqd yoki Karta bo'lsa
    else:
        category, _ = ExpenseCategory.objects.get_or_create(name="Ombor kirimi uchun")
        expense_payment_type = 'card' if 'kart' in p_type_name else 'cash'

        # Double-submit (ikki marta tushib qolish) oldini olish uchun tekshiruv:
        # Agar shu sonli chek allaqachon xarajatga yozilgan bo'lsa, qayta yaratmaymiz
        if not Expense.objects.filter(note__contains=f"#{new_check_number}").exists():
            Expense.objects.create(
                date=common_time.date(),
                category=category,
                amount=chek_umumiy_summasi,
                payment_type=expense_payment_type,
                note=f"Omborga kirim #{new_check_number}. Ta'minotchi: {supplier.name}",
                created_by_id=None
            )

        supplier.debt = Decimal('0.00')
        supplier.save()

    if employee_id:
        ActivityLog.objects.create(
            employee_id=employee_id,
            action=f"{new_check_number}-sonli chek bilan omborga kirim qildi"
        )

    return Response({
        "success": True,
        "message": "Kirim muvaffaqiyatli saqlandi",
        "data": {
            "check_number": new_check_number,
            "items_count": len(items),
            "total_amount": float(chek_umumiy_summasi)
        }
    })



#  INCOME DETAIL
@api_view(['GET'])
def income_check_details(request, check_number=None):
    if check_number is None:
        checks = WarehouseIncome.objects.values('check_number').distinct().order_by('-check_number')
        result = []

        for check in checks:
            number = check['check_number']
            if number is None:
                continue

            incomes = WarehouseIncome.objects.filter(check_number=number)
            total = incomes.aggregate(total_sum=Sum('quantity'))
            first_income = incomes.first()

            #  To'lov turini xavfsiz o'qib olamiz (Eski chala ma'lumotlar bo'lsa portlamaydi)
            p_type_name = first_income.payment_type.name if first_income and first_income.payment_type else "-"
            p_type_id = first_income.payment_type.id if first_income and first_income.payment_type else None

            products = []
            for income in incomes:
                products.append({
                    "product": income.product.name if income.product else "Mahsulot o'chirilgan",
                    "quantity": income.quantity,
                    "price": income.price
                })

            result.append({
                "check_number": number,
                # MANA SHU IKKITA QATORNI QO'SHTIK:
                "payment_type": p_type_name,  # Masalan: "Naqd", "Karta"
                "payment_type_id": p_type_id,  # Masalan: 1, 2
                "supplier": first_income.supplier.name if first_income and first_income.supplier else "-",
                "date": first_income.created_at if first_income else None,
                "total_quantity": total['total_sum'],
                "products": products
            })

        return Response(result)

    # -------------------------------------------------------------
    #  Bitta aniq chek raqami yuborilgandagi qismi:
    incomes = WarehouseIncome.objects.filter(check_number=check_number)
    if not incomes.exists():
        return Response({"error": "Kirim chek topilmadi"}, status=404)

    total = incomes.aggregate(total_sum=Sum('quantity'))
    first_income = incomes.first()

    #  Bu yerda ham to'lov turini xavfsiz o'qib olamiz
    p_type_name = first_income.payment_type.name if first_income and first_income.payment_type else "-"
    p_type_id = first_income.payment_type.id if first_income and first_income.payment_type else None

    products = []
    for income in incomes:
        products.append({
            "product": income.product.name if income.product else "Mahsulot o'chirilgan",
            "quantity": income.quantity,
            "price": income.price
        })

    return Response({
        "check_number": check_number,
        #  BU YERGA HAM QO'SHTIK:
        "payment_type": p_type_name,
        "payment_type_id": p_type_id,
        "supplier": first_income.supplier.name if first_income and first_income.supplier else "-",
        "date": first_income.created_at if first_income else None,
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

    def delete(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)  # xodim modelingiz nomi
        # Xodim ismini olish (modelizga qarab 'name' yoki 'first_name' qiling)
        emp_name = getattr(employee, 'name', getattr(employee, 'first_name', str(employee)))

        ArchivedItem.objects.create(
            item_type='employee',
            name=emp_name,
            original_id=employee.id,
            status="O'chirilgan"
        )
        employee.delete()
        return Response({"message": "Xodim o'chirildi va arxivlandi"}, status=status.HTTP_204_NO_CONTENT)
# ROLE uchun crud amallari
class RoleViewSet(ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        from .models import ArchivedItem

        ArchivedItem.objects.create(
            item_type='role',  # Buni ham models.py dagi ITEM_TYPES listiga qo'shib qo'ying
            name=instance.name,
            original_id=instance.id,
            status="O'chirilgan"
        )
        instance.delete()
        return Response({"message": "Rol o'chirildi va arxivlandi"}, status=status.HTTP_204_NO_CONTENT)


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
# @api_view(['GET'])
# def cash_flow_trend(request):
#
#     sana_from = request.GET.get('sana_from')
#     sana_to = request.GET.get('sana_to')
#
#     sales = Sale.objects.all()
#     incomes = WarehouseIncome.objects.all()
#
#     if sana_from and sana_to:
#         sales = sales.filter(created_at__date__range=[sana_from, sana_to])
#         incomes = incomes.filter(created_at__date__range=[sana_from, sana_to])
#
#     sales_data = sales.annotate(
#         date=TruncDate('created_at')
#     ).values('date').annotate(
#         total_in=Sum('total_price')
#     ).order_by('date')
#
#     expense_data = incomes.annotate(
#         date=TruncDate('created_at')
#     ).values('date').annotate(
#         total_out=Sum('total_price')
#     ).order_by('date')
#
#     return Response({
#         "sales": sales_data,
#         "expenses": expense_data
#     })


# CASH FLOW DAILY TABLE
@api_view(['GET'])
def cash_flow_daily(request):
    # 1. Savdolarni soatbay guruhlash
    sales_query = Sale.objects.annotate(
        hour_bucket=TruncHour('created_at')
    ).values('hour_bucket').annotate(
        total_in=Sum('total_price')
    ).order_by('hour_bucket')

    # 2. Xarajatlarni (Kirimlar) soatbay guruhlash
    incomes_query = WarehouseIncome.objects.annotate(
        hour_bucket=TruncHour('created_at')
    ).values('hour_bucket').annotate(
        total_out=Sum('total_price')
    ).order_by('hour_bucket')

    # Frontend uchun sanani "YYYY-MM-DD HH:MM" ko'rinishida formatlaymiz
    sales_data = [
        {
            "date": item['hour_bucket'].strftime("%Y-%m-%d %H:%M") if item['hour_bucket'] else "Noma'lum",
            "total_in": float(item['total_in']) if item['total_in'] else 0.0
        }
        for item in sales_query
    ]

    incomes_data = [
        {
            "date": item['hour_bucket'].strftime("%Y-%m-%d %H:%M") if item['hour_bucket'] else "Noma'lum",
            "total_out": float(item['total_out']) if item['total_out'] else 0.0
        }
        for item in incomes_query
    ]

    return Response({
        "sales": sales_data,
        "expenses": incomes_data
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
    permission_classes = [AllowAny]
    # 1. ASOSIY STATISTIKA (SUMMARY)
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        sana_from = request.GET.get('date_from')
        sana_to = request.GET.get('date_to')
        sales = Sale.objects.all()
        warehouse_incomes = WarehouseIncome.objects.all()
        other_expenses = Expense.objects.filter(is_deleted=False)
        if sana_from and sana_to:
            sales = sales.filter(created_at__date__range=[sana_from, sana_to])
            warehouse_incomes = warehouse_incomes.filter(created_at__date__range=[sana_from, sana_to])
            other_expenses = other_expenses.filter(date__range=[sana_from, sana_to])
        total_sales = sales.aggregate(total=Sum('total_price'))['total'] or 0
        total_expense = (warehouse_incomes.aggregate(total=Sum('total_price'))['total'] or 0) + \
                        (other_expenses.aggregate(total=Sum('amount'))['total'] or 0)
        nasiya_qs = sales.filter(payment_type__icontains='Nasiya')
        nasiya_sum = nasiya_qs.aggregate(total=Sum('total_price'))['total'] or 0
        nasiya_count = nasiya_qs.count()
        # O'sish foizi (Growth)
        growth_percent = 0
        if sana_from and sana_to:
            try:
                d1 = datetime.strptime(sana_from, '%Y-%m-%d')
                d2 = datetime.strptime(sana_to, '%Y-%m-%d')
                p_s1, p_s2 = d1 - relativedelta(months=1), d2 - relativedelta(months=1)
                prev_sales = \
                Sale.objects.filter(created_at__date__range=[p_s1, p_s2]).aggregate(total=Sum('total_price'))[
                    'total'] or 0
                if prev_sales > 0:
                    growth_percent = ((total_sales - prev_sales) / prev_sales) * 100
            except:
                pass
        return Response({
            "success": True,
            "data": {
                "total_sales": total_sales,
                "total_expenses": total_expense,
                "net_cash": total_sales - total_expense,
                "nasiya_sum": nasiya_sum,
                "nasiya_count": nasiya_count,
                "growth_percent": round(growth_percent, 2)
            }
        })
    # 2. KIRIM-CHIQIM (CASH FLOW)
    @action(detail=False, methods=['get'], url_path='cash-flow')
    def cash_flow(self, request):
        sana_from = request.GET.get('date_from')
        sana_to = request.GET.get('date_to')
        sales = Sale.objects.all()
        expenses = Expense.objects.filter(is_deleted=False)
        if sana_from and sana_to:
            sales = sales.filter(created_at__date__range=[sana_from, sana_to])
            expenses = expenses.filter(date__range=[sana_from, sana_to])
        cat_expenses = expenses.values('category__name').annotate(total=Sum('amount'))
        # Grafik trendi
        trend_data = sales.annotate(day=TruncDate('created_at')).values('day').annotate(
            kirim=Sum('total_price')).order_by('day')
        return Response({
            "success": True,
            "data": {
                "categories": [{"name": c['category__name'] or "Boshqa", "value": c['total']} for c in cat_expenses],
                "trend": list(trend_data)
            }
        })
    # 3. TOP PRODUCTS (SaleItem orqali hisoblash)
    @action(detail=False, methods=['get'], url_path='top-products')
    def top_products(self, request):
        # Bu qism grafikka ma'lumot tayyorlab beradi
        data = SaleItem.objects.values('product__name').annotate(
            total_sum=Sum(F('price') * F('quantity'))
        ).order_by('-total_sum')[:5]

        # Frontendga tushunarli formatga o'tkazamiz
        result = [{"product": i['product__name'], "total": i['total_sum']} for i in data]

        return Response({
            "success": True,
            "data": result
        })
    # 4. CREDIT ANALYTICS
    @action(detail=False, methods=['get'], url_path='credit-analytics')
    def credit_analytics(self, request):
        # payment_type__icontains deb yozsangiz xato yo'qoladi
        debtors_sum = Sale.objects.filter(payment_type__icontains='Nasiya').aggregate(total=Sum('total_price'))[
                          'total'] or 0
        return Response({
            "success": True,
            "data": {
                "total_debt": debtors_sum,
                "risky_count": 5,
                "debt_list": []
            }
        })
    # 5. TO'LOV TURLARi
    @action(detail=False, methods=['get'], url_path='payment-types')
    def payment_types(self, request):
        sales = Sale.objects.all()
        types = Sale.objects.values_list('payment_type', flat=True).distinct()
        data = []
        for p_type in types:
            if p_type:
                amount = sales.filter(payment_type=p_type).aggregate(total=Sum('total_price'))['total'] or 0
                data.append({"type": p_type, "amount": amount})
        return Response({"success": True, "data": data})

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













