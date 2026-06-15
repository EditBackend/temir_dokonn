import random
import requests
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Company, Employee, TariffPlan, CompanySubscription, VerificationCode

# TELEGRAM BOT MA'LUMOTLARI (Domla aytgan bot tokenini shu yerga qo'ying)
TELEGRAM_BOT_TOKEN = "8837150918:AAFCLCzlPXILiaktZy8OHP28ynntXlYiRVY"
TELEGRAM_CHAT_ID = "7724173791"  # Guruh yoki admin ID si


def send_otp_via_telegram(phone, code):
    """ Tasdiqlash kodini Telegram bot orqali yuborish funksiyasi """
    text = f"📱 Tizim: Temir Do'kon\n📞 Telefon: {phone}\n🔑 Tasdiqlash kodi: {code}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram yuborishda xato: {e}")


# Telefon raqam kiritilganda OTP kod yuborish
@api_view(['POST'])
@permission_classes([AllowAny])
def register_request(request):
    phone = request.data.get('phone')
    if not phone:
        return Response({"error": "Telefon raqam shart!"}, status=400)

    # 6 xonali tasodifiy kod yaratish
    code = str(random.randint(100000, 999999))
    VerificationCode.objects.create(phone=phone, code=code)

    # Telegram bot orqali jo'natish
    send_otp_via_telegram(phone, code)

    return Response({"success": True, "message": "Tasdiqlash kodi botga yuborildi."})


# Kelgan kodni tekshirish va CEO profilini ochish
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_ceo(request):
    phone = request.data.get('phone')
    code = request.data.get('code')
    name = request.data.get('name')  # Ism-familiya

    otp = VerificationCode.objects.filter(phone=phone, code=code, is_used=False).order_by('-id').first()
    if not otp or not otp.is_valid():
        return Response({"error": "Kod noto'g'ri yoki muddati o'tgan!"}, status=400)

    otp.is_used = True
    otp.save()

    # Xodim (CEO) sifatida vaqtinchalik saqlash
    employee, created = Employee.objects.get_or_create(
        phone=phone,
        defaults={'name': name, 'is_ceo': True, 'is_verified': True, 'password': make_password('temporary_pass')}
    )

    return Response({"success": True, "message": "Telefon raqam tasdiqlandi. Endi kompaniya yarating."})


# Kompaniya yaratish va 7 kunlik demo berish
@api_view(['POST'])
@permission_classes([AllowAny])
def create_company(request):
    phone = request.data.get('phone')  # Tasdiqlangan telefon
    company_name = request.data.get('company_name')
    password = request.data.get('password')

    try:
        employee = Employee.objects.get(phone=phone, is_verified=True, company__isnull=True)
    except Employee.DoesNotExist:
        return Response({"error": "Avval telefon raqamni tasdiqlang yoki kompaniya allaqachon ochilgan!"}, status=400)

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


#  Tizimga kirish (Login)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_employee(request):
    phone = request.data.get('phone')
    password = request.data.get('password')

    try:
        employee = Employee.objects.get(phone=phone, is_verified=True)
    except Employee.DoesNotExist:
        return Response({"error": "Foydalanuvchi topilmadi!"}, status=404)

    if not check_password(password, employee.password):
        return Response({"error": "Parol noto'g'ri!"}, status=400)

    # Subskripsiyani tekshirish
    sub = CompanySubscription.objects.filter(company=employee.company, status__in=['active', 'trialing']).last()
    if not sub or sub.end_date < timezone.now():
        if sub:
            sub.status = 'expired'
            sub.save()
        return Response({"error": "Sizning tarif muddatingiz tugagan! Iltimos to'lov qiling."}, status=402)

    return Response({
        "success": True,
        "token": "MOCK_TOKEN_XYZ123",  # Agar JWT bo'lsa o'zingizni token generatorni qo'ying
        "user": {
            "name": employee.name,
            "is_ceo": employee.is_ceo,
            "company": employee.company.name if employee.company else None
        }
    })


# Parolni unutganda kod yuborish
@api_view(['POST'])
@permission_classes([AllowAny])
def forget_password(request):
    phone = request.data.get('phone')
    if not Employee.objects.filter(phone=phone).exists():
        return Response({"error": "Bu raqamli xodim tizimda yo'q!"}, status=44)

    code = str(random.randint(100000, 999999))
    VerificationCode.objects.create(phone=phone, code=code)
    send_otp_via_telegram(phone, code)

    return Response({"success": True, "message": "Parolni tiklash kodi Telegram botga yuborildi."})


# Yangi parolni saqlash
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    phone = request.data.get('phone')
    code = request.data.get('code')
    new_password = request.data.get('new_password')

    otp = VerificationCode.objects.filter(phone=phone, code=code, is_used=False).order_by('-id').first()
    if not otp or not otp.is_valid():
        return Response({"error": "Kod xato yoki muddati o'tgan!"}, status=400)

    otp.is_used = True
    otp.save()

    employee = Employee.objects.get(phone=phone)
    employee.password = make_password(new_password)
    employee.save()

    return Response({"success": True, "message": "Parolingiz muvaffaqiyatli yangilandi!"})