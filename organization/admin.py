from django.contrib import admin
from .models import Company, Employee, TariffPlan, CompanySubscription, VerificationCode

# 1. Kompaniyalar boshqaruvi
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'created_at') # Admin panel ro'yxatida ko'rinadigan ustunlar
    search_fields = ('name', 'phone') # Ismi va telefoni bo'yicha qidirish tizimi
    list_filter = ('created_at',) # O'ng tomondagi sana bo'yicha filter
    ordering = ('-id',) # Yangi ochilganlari eng tepada turadi

# 2. Xodimlar (Employee) boshqaruvi — Telefon raqamni shu yerdan o'chirishadi
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'company', 'is_ceo', 'is_verified')
    search_fields = ('name', 'phone', 'company__name') # Ism, telefon va kompaniya nomi bo'yicha qidiruv
    list_filter = ('is_ceo', 'is_verified', 'company') # CEO yoki tasdiqlanganligiga ko'ra filterlash
    ordering = ('-id',)

# 3. Tariflar boshqaruvi
@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'duration_days', 'monthly_price')
    search_fields = ('name',)

# 4. Subskripsiyalar (Tarif muddatlari) boshqaruvi
@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'tariff', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'tariff', 'end_date')
    search_fields = ('company__name',)

# 5. OTP Kodlar tarixi (Kimga qaysi kod ketganini ko'rish uchun)
@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone', 'code', 'is_used', 'created_at')
    search_fields = ('phone', 'code')
    list_filter = ('is_used', 'created_at')