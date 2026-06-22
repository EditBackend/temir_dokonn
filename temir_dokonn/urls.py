from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.views import home

urlpatterns = [
    # 1. Admin panel
    path('admin/', admin.site.urls),

    # 2. Avtorizatsiya va tashkilot yo'llari (Buni tepaga olib chiqamiz)
    # Yakuniy url: api/auth/forget-password/ va hokazo bo'ladi
    path('api/', include('organization.urls')),

    # 3. Qolgan barcha umumiy API pichoqlari (CRUD, ViewSet'lar)
    path('api/', include('api.urls')),

    # 4. Bosh sahifa
    path('', home),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)