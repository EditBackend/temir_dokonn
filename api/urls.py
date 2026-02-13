from django.urls import path
from .views import (
    ProductViewSet,
    SaleViewSet,
    CategoryViewSet,
    sales_summary,
    home
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

    path('sales-summary/', sales_summary),
]
