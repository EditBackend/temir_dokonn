from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    ProductViewSet, SaleViewSet, CategoryViewSet, sales_summary, home,
    last_check_number, new_check_number, check_details, income_check_details,
    create_income, SupplierViewSet, CustomerViewSet, real_profit, login_employee,
    EmployeeViewSet, RoleViewSet, BatchViewSet, cash_flow, cash_flow_daily,
    expense_categories, monthly_trend, monthly_summary, monthly_comparison,
    best_worst_day, activity_list, DashboardViewSet, ExpenseCategoryList,
    ExpenseViewSet, ExpenseAnalyticsView, TopProductsView, debtors_list,
    credit_aging, credit_summary, recent_payments, debtor_detail,
    ProductsTableView, abc_xyz_analysis_optimized, UnitViewSet,
    EmployeeDetailView, RoleDetailView, archive_list, customer_profile_details,
    receive_customer_payment, role_permissions_management
)

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'units', UnitViewSet)
router.register(r'roles', RoleViewSet, basename='role')

expense_list = ExpenseViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

expense_detail = ExpenseViewSet.as_view({
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # HOME & ROUTER SYSTEM
    path('', home),
    path('', include(router.urls)),

    # EMPLOYEES
    path('employees/', EmployeeViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),

    # CATEGORY
    path('categories/', CategoryViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('categories/<int:pk>/', CategoryViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),

    # PRODUCTS
    path('products/', ProductViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('products/<int:pk>/', ProductViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),
    path('products/top/', DashboardViewSet.as_view({'get': 'top_products'})),
    path('top-products/', TopProductsView.as_view()),
    path('products-table/', ProductsTableView.as_view()),

    # SUPPLIERS
    path('suppliers/', SupplierViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('suppliers/<int:pk>/', SupplierViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),

    # CUSTOMERS & PROFILE & PAYMENTS
    path('customers/', CustomerViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('customers/<int:pk>/', CustomerViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),
    path('customers/<int:customer_id>/profile/', customer_profile_details, name='customer-profile'),
    path('customers/<int:customer_id>/pay/', receive_customer_payment, name='customer-pay'),

    # SALES & CHECKS
    path('sales/', SaleViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('sales/<int:pk>/', SaleViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),
    path('sales-summary/', sales_summary),
    path('check/', check_details),
    path('check/<int:check_number>/', check_details),
    path('income-check/', income_check_details),
    path('income-check/<int:check_number>/', income_check_details),
    path('last-check/', last_check_number),
    path('new-check/', new_check_number),

    # WAREHOUSE INCOME & PROFIT
    path('create-income/', create_income),
    path('real-profit/', real_profit),
    path('abc-xyz-analysis/', abc_xyz_analysis_optimized),

    # BATCHES
    path('batches/', BatchViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('batches/<int:pk>/', BatchViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),
    path('batches/<int:pk>/sell/', BatchViewSet.as_view({'post': 'sell'})),
    path('batches/alerts/', BatchViewSet.as_view({'get': 'alerts'})),

    # CASH FLOW & ANALYTICS
    path('cash-flow/', cash_flow),
    path('cash-flow/trend/', DashboardViewSet.as_view({'get': 'cash_flow'})),
    path('cash-flow/daily/', cash_flow_daily),
    path('cash-flow/categories/', expense_categories),

    # MONTHLY REPORT
    path('monthly/summary/', monthly_summary),
    path('monthly/trend/', monthly_trend),
    path('monthly/comparison/', monthly_comparison),
    path('monthly/best-worst/', best_worst_day),
    path('activity/', activity_list),

    # EXPENSES MODULE
    path('expenses/categories/', ExpenseCategoryList.as_view()),
    path('expenses/categories/<int:pk>/', ExpenseCategoryList.as_view()),
    path('expenses/', expense_list),
    path('expenses/<int:pk>/', expense_detail),
    path('expenses/analytics/by-category/', ExpenseAnalyticsView.as_view()),
    path('analytics/top-products/', TopProductsView.as_view()),

    # CREDITS & DEBTORS
    path('credits/analytics/summary/', credit_summary),
    path('credits/analytics/aging/', credit_aging),
    path('credits/debtors/', debtors_list),
    path('credits/payments/recent/', recent_payments),
    path('credits/debtors/<int:customer_id>/', debtor_detail),

    # ROLES PERMISSIONS
    path('roles/<int:role_id>/permissions/', role_permissions_management, name='role-permissions'),

    # AUTH LOGIN
    path('login/', login_employee),

# Frontendchiga qulay bo'lishi uchun ikkala variantni ham qo'shib qo'yamiz:
    path('archive/', views.archive_list, name='archive-old'),
    path('archive-list/', views.archive_list, name='archive-list'),
]

urlpatterns += router.urls