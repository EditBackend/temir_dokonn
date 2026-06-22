from django.contrib import admin
from .models import Company, Employee, TariffPlan, CompanySubscription, VerificationCode

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'created_at')
    search_fields = ('name', 'phone')
    list_filter = ('created_at',)
    ordering = ('-id',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # 🟢 Djangoning ichki xavfsizlik maydonlarini ham qo'shib qo'yamiz:
    list_display = ('id', 'name', 'phone', 'company', 'is_ceo', 'is_verified', 'is_active', 'is_staff')
    search_fields = ('name', 'phone', 'company__name')
    list_filter = ('is_ceo', 'is_verified', 'is_active', 'company')
    ordering = ('-id',)

@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'duration_days', 'monthly_price')
    search_fields = ('name',)

@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'tariff', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'tariff', 'end_date')
    search_fields = ('company__name',)

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone', 'code', 'is_used', 'created_at')
    search_fields = ('phone', 'code')
    list_filter = ('is_used', 'created_at')