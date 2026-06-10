from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import UnitViewSet, RoleDetailView, archive_list, customer_profile_details, \
    receive_customer_payment, role_permissions_management  # Buni views.py da yozganmiz
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
    cash_flow_daily,
    # cash_flow_trend,
    expense_categories,
    monthly_trend,
    monthly_summary,
    monthly_comparison,
    best_worst_day,
    # top_products,
    activity_list,
    DashboardViewSet,
    ExpenseCategoryList,
    ExpenseViewSet,
    ExpenseAnalyticsView,
    TopProductsView,
    debtors_list,
    credit_aging,
    credit_summary,
    recent_payments,
    debtor_detail,
    ProductsTableView,
    abc_xyz_analysis_optimized, UnitViewSet,
    EmployeeDetailView,

)

#  ROUTER
router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'units', UnitViewSet) # Bu avtomatik CRUD yo'llarini yaratadi

#  Expense ViewSet
expense_list = ExpenseViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

expense_detail = ExpenseViewSet.as_view({
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
# Employee uchun detail yo'li (PATCH va DELETE uchun)
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),

    # Frontendchi so'rayotgan "api/products/top/" yo'lini dashboardga yo'naltiramiz
    # Shunda u o'zgartirishi shart bo'lmaydi
    path('products/top/', DashboardViewSet.as_view({'get': 'top_products'})),
    path('', home),
    path('', include(router.urls)),
    # CATEGORY (OLD)
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

    # CHECK NUMBER
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

    path('roles/<int:pk>/', RoleDetailView.as_view(), name='role-detail'),
    # as_manager emas, as_view bo'ladi!
    # EMPLOYEES
    path('employees/', EmployeeViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    # BATCHES
    path('batches/', BatchViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('batches/<int:pk>/', BatchViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
    path('batches/<int:pk>/sell/', BatchViewSet.as_view({
        'post': 'sell'
    })),
    path('batches/alerts/', BatchViewSet.as_view({
        'get': 'alerts'
    })),

    # CASH FLOW
    path('cash-flow/', cash_flow),
    # Eski URL'ni dashboard ichidagi tayyor 'cash_flow' funksiyasiga yo'naltiramiz:
    path('cash-flow/trend/', DashboardViewSet.as_view({'get': 'cash_flow'})),
    path('cash-flow/daily/', cash_flow_daily),
    path('cash-flow/categories/', expense_categories),

    # MONTHLY
    path('monthly/summary/', monthly_summary),
    path('monthly/trend/', monthly_trend),
    path('monthly/comparison/', monthly_comparison),
    path('monthly/best-worst/', best_worst_day),

    # API
    # path('products/top/', top_products),
    path('activity/', activity_list),

    #EXPENSES MODULE
    path('expenses/categories/', ExpenseCategoryList.as_view()),
    path('expenses/categories/<int:pk>/', ExpenseCategoryList.as_view()),
    path('expenses/', expense_list),
    path('expenses/<int:pk>/', expense_detail),
    path('expenses/analytics/by-category/', ExpenseAnalyticsView.as_view()),

    #EXPENSES MODULE
    path('expenses/categories/', ExpenseCategoryList.as_view()),
    path('expenses/categories/<int:pk>/', ExpenseCategoryList.as_view()), # Mana shu qator aniq tursin
    #TOP PRODUCTS (NEW ANALYTICS)
    path('analytics/top-products/', TopProductsView.as_view()),
    #Kredit analitikalari
    path('credits/analytics/summary/', credit_summary),
    path('credits/analytics/aging/', credit_aging),
    path('credits/debtors/', debtors_list),
    path('credits/payments/recent/', recent_payments),
    path('credits/debtors/<int:customer_id>/', debtor_detail),

    #top products alohida oyna
    path('top-products/', TopProductsView.as_view()),
    path('products-table/', ProductsTableView.as_view()),

    # abc analiz
    path('abc-xyz-analysis/', abc_xyz_analysis_optimized),
#  Frontendchi qidirayotgan grafik yo'lagini dashboard ichidagi tayyor funksiyaga ulab qo'yamiz
    path('api/cash-flow/trend/', DashboardViewSet.as_view({'get': 'cash_flow'})),
    path('archive/', archive_list),

    # urls.py ichiga qo'shing:
    path('customers/<int:customer_id>/profile/', customer_profile_details, name='customer-profile'),
    path('customers/<int:customer_id>/pay/', receive_customer_payment, name='customer-pay'),
    path('roles/<int:role_id>/permissions/', role_permissions_management, name='role-permissions'),
]

#  MUHIM
urlpatterns += router.urls