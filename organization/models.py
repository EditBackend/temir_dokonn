from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.utils import timezone


class TenantModel(models.Model):
    # Har bir ma'lumot qaysi kompaniyaga tegishli ekanligini belgilaydi
    company = models.ForeignKey(
        'organization.Company',
        on_delete=models.CASCADE,
        related_name="%(class)s_related", # Har bir model uchun unikal nom yaratadi
        null=True,
        blank=True
    )

    class Meta:
        abstract = True # Bazada alohida jadval bo'lib tushmaydi, faqat meros beradi


#  Kompaniya modeli
class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Kompaniya nomi")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

#  Xodim/Foydalanuvchi modeli (Agar loyihada custom user bo'lmasa, shuni ishlating)
class Employee(models.Model):
    # Agar loyihada tayyor User bo'lsa, shunga OneToOne qiling, yoki AbstractUser ishlating
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=255) # Hashlangan parol uchun
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees', null=True, blank=True)
    is_ceo = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False) # SMS/Telegram orqali tasdiqlanganmi?

    def __str__(self):
        return f"{self.name} ({self.phone})"

# Tariflar modeli
class TariffPlan(models.Model):
    name = models.CharField(max_length=100)
    duration_days = models.IntegerField(default=30)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# Obuna/Shartnoma tarixi modeli
class CompanySubscription(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions')
    tariff = models.ForeignKey(TariffPlan, models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, default='active') # active, expired, trialing

    def __str__(self):
        return f"{self.company.name} - {self.tariff.name}"

#  Bir martalik kodlarni saqlash (OTP)
class VerificationCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=5) and not self.is_used