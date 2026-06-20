from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from datetime import timedelta
from django.utils import timezone


class TenantModel(models.Model):
    company = models.ForeignKey(
        'organization.Company',
        on_delete=models.CASCADE,
        related_name="%(class)s_related",
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


# ==========================================
# 🟢 CUSTOM USER MANAGER (Employee uchun shart)
# ==========================================
class EmployeeManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Telefon raqam bo'lishi shart!")
        extra_fields.setdefault('is_verified', True)

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)  # Parolni xavfsiz hashlaydi
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_ceo', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(phone, password, **extra_fields)


#  Kompaniya modeli
class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Kompaniya nomi")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ==========================================
# 🟢 YANGILANGAN XODIM/USER MODELI
# ==========================================
class Employee(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    # password maydoni AbstractBaseUser ichida bor, shuning uchun bu yerga qayta yozish shart emas!

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees', null=True, blank=True)
    is_ceo = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # Django Admin paneli va ruxsatnomalar tizimi uchun majburiy maydonlar:
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Yuqoridagi Custom Managerni ulaymiz
    objects = EmployeeManager()

    # 🟢 DJANGO TIZIMI TANISHI UCHUN ENG ASOSIY SATTINGLAR:
    USERNAME_FIELD = 'phone'  # Login maydoni sifatida telefon ishlatiladi
    REQUIRED_FIELDS = ['name']  # Superuser ochayotganda majburiy so'raladigan maydon

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
    status = models.CharField(max_length=20, default='active')

    def __str__(self):
        return f"{self.company.name} - {self.tariff.name}"


# OTP Kodlar
class VerificationCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        eskirish_muddati = self.created_at + timedelta(minutes=2)
        return timezone.now() <= eskirish_muddati