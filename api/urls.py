from django.urls import path
from .views import (
    ProductViewSet,
    SaleViewSet,
    CategoryViewSet,
    sales_summary,
    home,
    last_check_number,
    new_check_number,
    check_details,
    income_check_details,
    create_income,
    SupplierViewSet,
    CustomerViewSet,
    real_profit,
    login_employee,
    EmployeeViewSet,
    RoleViewSet,
    BatchViewSet,
    cash_flow,
)

urlpatterns = [

    path('', home),

    # CATEGORY
    path('categories/', CategoryViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('categories/<int:pk>/', CategoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),

    # PRODUCTS
    path('products/', ProductViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('products/<int:pk>/', ProductViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),

    # SUPPLIERS
    path('suppliers/', SupplierViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('suppliers/<int:pk>/', SupplierViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),

    # CUSTOMERS
    path('customers/', CustomerViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('customers/<int:pk>/', CustomerViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),

    # SALES
    path('sales/', SaleViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('sales/<int:pk>/', SaleViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),

    # SALES SUMMARY
    path('sales-summary/', sales_summary),

    # CHECK SYSTEM
    path('check/', check_details),
    path('check/<int:check_number>/', check_details),

    # INCOME CHECK
    path('income-check/', income_check_details),
    path('income-check/<int:check_number>/', income_check_details),

    # CASH FLOW
    path('last-check/', last_check_number),
    path('new-check/', new_check_number),

    # WAREHOUSE INCOME
    path('create-income/', create_income),

    # REAL PROFIT
    path('real-profit/', real_profit),

    # LOGIN
    path('login/', login_employee),

    # ROLES
    path('roles/', RoleViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),

    # EMPLOYEES
    path('employees/', EmployeeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),

    # batch list / create
    path('batches/', BatchViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),

    # batch detail
    path('batches/<int:pk>/', BatchViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),

    # batch sell (FIFO test uchun)
    path('batches/<int:pk>/sell/', BatchViewSet.as_view({
        'post': 'sell'
    })),

    # dead stock alert
    path('batches/alerts/', BatchViewSet.as_view({
        'get': 'alerts'
    })),
    # CASH FLOW
    path('cash-flow/', cash_flow),
]