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
from .models import Company, Employee, TariffPlan, CompanySubscription, VerificationCode



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


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_ceo(request):
    phone = request.data.get('phone')
    code = request.data.get('code')

    # Frontendchi 'name' yoki 'first_name' yuborsa ham o'qib oladigan qilamiz
    name = request.data.get('name') or request.data.get('first_name')

    # 1. Kod va telefonni tekshirish
    otp = VerificationCode.objects.filter(phone=phone, code=code, is_used=False).order_by('-id').first()
    if not otp or not otp.is_valid():
        return Response({"error": "Kod noto'g'ri yoki muddati o'tgan!"}, status=400)

    # XAVFSIZLIK: Agar frontendchi baribir ism yubormagan bo'lsa, bazani asrab qolish uchun vaqtinchalik nom beramiz
    if not name:
        name = f"CEO_{phone[-4:]}"  # Masalan: CEO_1814 deb yozib ketadi bazaga, keyingi bosqichda to'g'irlasa bo'ladi
        # Yoki xohlasangiz qattiq tekshiruv qo'ying:
        # return Response({"error": "Ism-familiya (name) maydoni majburiy!"}, status=400)

    otp.is_used = True
    otp.save()

    # Xodim (CEO) sifatida vaqtinchalik saqlash
    employee, created = Employee.objects.get_or_create(
        phone=phone,
        defaults={
            'name': name,  #  Endi bu yerga null tushmaydi!
            'is_ceo': True,
            'is_verified': True,
            'password': make_password('temporary_pass')
        }
    )

    # Agar xodim allaqachon mavjud bo'lsa-yu, lekin ismi o'zgargan bo'lsa yangilab qo'yamiz
    if not created and employee.name != name:
        employee.name = name
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

#  Tizimga kirish (Login) - YAKUNIY VA XAVFSIZ VARIANT
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

    # 🟢 TOKEnni qo'lda yaratamiz, lekin TenantViewSetMixin taniy olishi uchun
    # xodimning haqiqiy ID sini 'user_id' kalitiga yozamiz:
    refresh = RefreshToken()
    refresh['user_id'] = employee.id  #  Mana shu yerda haqiqiy ID (masalan 21) ketadi
    refresh['username'] = employee.phone

    return Response({
        "success": True,
        "token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "user": {
            "id": employee.id,
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