"""
Django settings for temir_dokonn project.
"""

from pathlib import Path
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# SECURITY
# ========================
SECRET_KEY = 'django-insecure-6#5&%g7@q(-&81^ehb1&m*+x9$+q0@%0+7r6#0b4ad(=zpm_ap'
DEBUG = True

ALLOWED_HOSTS = [
    "temir-dokonn-7.onrender.com",
    "localhost",
    "127.0.0.1",
]

# ========================
# APPLICATIONS
# ========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',  # CORS har doim tepada tursin
    'rest_framework',
    'drf_spectacular',
    'api',
    'organization',
]

# ========================
# MIDDLEWARE
# ========================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  <-- SHU QATORNI KOMMENTGA OLING
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'temir_dokonn.urls'

# ========================
# CORS / CSRF SOZLAMALARI
# ========================
CORS_ALLOW_ALL_ORIGINS = True # Test jarayonida hamma narsaga ruxsat beradi
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://temir-dokonn-7.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Brauzer cookielarini ruxsat berish
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True



# temir_dokonn/settings.py

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 1000,
    #  Djangoning o'z standart SimpleJWT va Session autentifikatsiyasini qaytaramiz
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# 🟢 Simple JWT ga sizning xodimlar modelingizni to'g'ri ulab qo'yamiz:
SIMPLE_JWT = {
    'USER_MODEL': 'organization.Employee',  # Token qidiriladigan asosiy model
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    # Qolgan token muddati (LIFETIME) sozlamalaringiz bo'lsa, pastidan o'zgarishsiz qolaversin...
}


# JWT token muddatlarini uzaytirish (Frontendchi har 5 daqiqada login qilmasligi uchun)
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_MODEL': 'organization.Employee',
    'USER_ID_FIELD': 'id',
}






WSGI_APPLICATION = 'temir_dokonn.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]




# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
#

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get(
            'DATABASE_URL',
            'postgresql://neondb_owner:npg_47bZwunGecog@ep-dawn-morning-apqufij2.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require'
        )
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'




