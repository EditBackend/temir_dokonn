import random
import requests
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status



from api.models import Employee
from .models import Company, TariffPlan, CompanySubscription, VerificationCode

TELEGRAM_BOT_TOKEN = "8837150918:AAFCLCzlPXILiaktZy8OHP28ynntXlYiRVY"
TELEGRAM_CHAT_ID = "7724173791"


def send_otp_via_telegram(phone, code):
    """ Tasdiqlash kodini Telegram bot orqali yuborish funksiyasi """
    text = f"📱 Tizim: Temir Do'kon\n📞 Telefon: {phone}\n🔑 Tasdiqlash kodi: {code}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram yuborishda xato: {e}")




@api_view(['POST'])
@permission_classes([AllowAny])
def register_request(request):
    phone = request.data.get('phone')
    if not phone:
        return Response({"error": "Telefon raqam shart!"}, status=status.HTTP_400_BAD_REQUEST)

    # 6 xonali tasodifiy kod yaratish
    code = str(random.randint(100000, 999999))
    VerificationCode.objects.create(phone=phone, code=code)

    # Telegram bot orqali jo'natish
    send_otp_via_telegram(phone, code)

    return Response({"success": True, "message": "Tasdiqlash kodi botga yuborildi."})

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_ceo(request):
    phone = request.data.get('phone')
    code = request.data.get('code')

    first_name = request.data.get('first_name') or request.data.get('name') or "CEO"

    # 1. Kod va telefonni tekshirish
    otp = VerificationCode.objects.filter(phone=phone, code=code, is_used=False).order_by('-id').first()
    if not otp or not otp.is_valid():
        return Response({"error": "Kod noto'g'ri yoki muddati o'tgan!"}, status=status.HTTP_400_BAD_REQUEST)

    otp.is_used = True
    otp.save()

    # 🟢 TO'G'RILANDI: Modelda fieldlar yo'qligi sababli xato bermasligi uchun xavfsiz get_or_create
    employee, created = Employee.objects.get_or_create(
        phone=phone,
        defaults={
            'is_ceo': True,
            'is_active': True,
            'password': make_password('temporary_pass')
        }
    )

    #  Agar modelda 'name' yoki 'first_name' bo'lsa, xato bermay sekingina saqlaymiz
    for field_name in ['name', 'first_name', 'full_name']:
        if hasattr(employee, field_name):
            setattr(employee, field_name, first_name)
            break

    employee.is_ceo = True
    employee.save()

    return Response({"success": True, "message": "Telefon raqam tasdiqlandi. Endi kompaniya yarating."})

# Kompaniya yaratish va 7 kunlik demo berish
@api_view(['POST'])
@permission_classes([AllowAny])
def create_company(request):
    phone = request.data.get('phone')  # Tasdiqlangan telefon
    company_name = request.data.get('company_name')
    password = request.data.get('password')

    try:
        # 🟢 TO'G'RILANDI: 'is_verified' maydoni modelda bo'lmagani uchun shartdan olib tashlandi
        employee = Employee.objects.get(phone=phone, company__isnull=True)
    except Employee.DoesNotExist:
        return Response({"error": "Avval telefon raqamni tasdiqlang yoki kompaniya allaqachon ochilgan!"},
                        status=status.HTTP_400_BAD_REQUEST)

    # Kompaniya ochish
    company = Company.objects.create(name=company_name, phone=phone)

    # Employee yangilash
    employee.company = company
    employee.password = make_password(password)
    employee.save()

    # 7 Kunlik Demo Tarifni ulash
    demo_tariff, _ = TariffPlan.objects.get_or_create(
        name="7 Kunlik Demo",
        duration_days=7,
        monthly_price=0
    )

    CompanySubscription.objects.create(
        company=company,
        tariff=demo_tariff,
        end_date=timezone.now() + timedelta(days=7),
        status='trialing'
    )

    return Response({"success": True, "message": "Kompaniya va 7 kunlik demo reja muvaffaqiyatli yaratildi!"})
@api_view(['POST'])
@permission_classes([AllowAny])
def login_employee(request):
    phone = request.data.get('phone')
    password = request.data.get('password')

    try:
        employee = Employee.objects.get(phone=phone, is_active=True)
    except Employee.DoesNotExist:
        return Response({"error": "Foydalanuvchi topilmadi!"}, status=status.HTTP_404_NOT_FOUND)

    if not check_password(password, employee.password):
        return Response({"error": "Parol noto'g'ri!"}, status=status.HTTP_400_BAD_REQUEST)

    if not employee.company:
        return Response({
            "error": "Sizda hali ro'yxatdan o'tgan kompaniya yo'q! Avval kompaniya yarating.",
            "code": "NO_COMPANY"
        }, status=status.HTTP_400_BAD_REQUEST)

    sub = CompanySubscription.objects.filter(company=employee.company, status__in=['active', 'trialing']).last()
    if not sub or sub.end_date < timezone.now():
        if sub:
            sub.status = 'expired'
            sub.save()
        return Response({"error": "Sizning tarif muddatingiz tugagan!"}, status=status.HTTP_402_PAYMENT_REQUIRED)

    refresh = RefreshToken.for_user(employee)
  
    #  TO'G'RILANDI Model fieldlaridan kelib chiqib, frontendga foydalanuvchi ismini xavfsiz uzatish
    user_display_name = getattr(employee, 'name', None) or getattr(employee, 'first_name', None) or "CEO"

    return Response({
        "success": True,
        "token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "user": {
            "id": employee.id,
            "first_name": user_display_name,
            "last_name": "",
            "is_ceo": getattr(employee, 'is_ceo', True),
            "company": employee.company.name if employee.company else None
        }
    }, status=status.HTTP_200_OK)
@api_view(['POST'])
@permission_classes([AllowAny])
def forget_password(request):
    phone = request.data.get('phone')
    if not Employee.objects.filter(phone=phone).exists():
        return Response({"error": "Bu raqamli xodim tizimda yo'q!"}, status=status.HTTP_400_BAD_REQUEST)

    code = str(random.randint(100000, 999999))
    VerificationCode.objects.create(phone=phone, code=code)
    send_otp_via_telegram(phone, code)

    return Response({"success": True, "message": "Parolni tiklash kodi Telegram botga yuborildi."})




@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    phone = request.data.get('phone')
    code = request.data.get('code')
    new_password = request.data.get('new_password')

    otp = VerificationCode.objects.filter(phone=phone, code=code, is_used=False).order_by('-id').first()
    if not otp or not otp.is_valid():
        return Response({"error": "Kod xato yoki muddati o'tgan!"}, status=status.HTTP_400_BAD_REQUEST)

    otp.is_used = True
    otp.save()

    try:
        employee = Employee.objects.get(phone=phone)
        employee.password = make_password(new_password)
        employee.save()
        return Response({"success": True, "message": "Parolingiz muvaffaqiyatli yangilandi!"})
    except Employee.DoesNotExist:
        return Response({"error": "Foydalanuvchi topilmadi!"}, status=status.HTTP_404_NOT_FOUND)