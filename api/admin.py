from django.contrib import admin
from .models import Product, Sale,Category, Supplier, WarehouseIncome



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price','category', 'quantity')
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')
    search_fields = ('name',)


@admin.register(WarehouseIncome)
class WarehouseIncomeAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'quantity', 'price', 'total_price')
    search_fields = ('product',)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'quantity',
        'price',
        'total_price',
        'customer',
        'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('product__name', 'customer')