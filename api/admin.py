from django.contrib import admin
from .models import (
    Branch, ExpenseCategory, Expense, Role, Employee,
    ActivityLog, Customer, Category, Product, Supplier,
    WarehouseIncome, Batch, Sale, SaleItem, PriceHistory, Payment
)

# 1. Branch (Filiallar)
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'created_at')
    search_fields = ('name', 'address')

# 2. Expense (Xarajatlar)
@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'category', 'amount', 'payment_type', 'created_by')
    list_filter = ('payment_type', 'date')
    search_fields = ('note',)

# 3. Employee & Roles (Xodimlar va Ruxsatlar)
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'can_sell', 'can_income', 'can_view_reports', 'can_manage_users')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'phone', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('first_name', 'last_name', 'phone')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'action', 'created_at')
    list_filter = ('created_at', 'employee')
    search_fields = ('action',)

# 4. Customer & Payments (Mijozlar va To'lovlar)
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'phone', 'debt', 'total_debt')
    search_fields = ('first_name', 'last_name', 'phone')
    list_editable = ('debt',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'date')
    list_filter = ('date',)

# 5. Inventory (Ombor va Mahsulotlar)
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'last_price', 'quantity', 'unity')
    list_filter = ('category', 'unity')
    search_fields = ('name',)
    list_editable = ('price', 'quantity')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone')
    search_fields = ('name', 'phone')

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_code', 'product', 'unit_cost', 'qty_in', 'qty_left', 'received_date')
    list_filter = ('received_date', 'product')
    search_fields = ('batch_code', 'product__name')

@admin.register(WarehouseIncome)
class WarehouseIncomeAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'quantity', 'price', 'total_price', 'payment_type', 'created_at')
    list_filter = ('payment_type', 'created_at', 'supplier')
    search_fields = ('product__name', 'check_number')

# 6. Sales (Sotuvlar)
class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity', 'price', 'total_price', 'customer', 'payment_type', 'created_at')
    list_filter = ('payment_type', 'created_at')
    search_fields = ('product__name', 'customer__first_name', 'customer__phone')
    inlines = [SaleItemInline] # Sotuv ichida sotilgan narsalarni ko'rish uchun

# 7. History (Tarix)
@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'old_price', 'new_price', 'changed_at', 'employee')
    list_filter = ('changed_at',)
    readonly_fields = ('old_price', 'new_price', 'changed_at')