from django.contrib import admin
from .models import Product, Sale



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'quantity')
    search_fields = ('name',)



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