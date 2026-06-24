import os
import sys
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps folder to sys.path to allow importing apps directly
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['.vercel.app']),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-default-key-change-it-in-production')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '.vercel.app', 'vercel.app'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Project apps
    'users.apps.UsersConfig',
    'products.apps.ProductsConfig',
    'orders.apps.OrdersConfig',
    'payments.apps.PaymentsConfig',
    'coupons.apps.CouponsConfig',
    'notifications.apps.NotificationsConfig',
    'dashboard.apps.DashboardConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'electro_shop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Custom context processor for notifications count and categories
                'products.context_processors.categories_processor',
                'orders.context_processors.cart_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'electro_shop.wsgi.application'
ASGI_APPLICATION = 'electro_shop.asgi.application'

# Database Configuration
# Fallback to SQLite if DB credentials are not set in .env
DB_NAME = env('DB_NAME', default='')
if DB_NAME:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
        }
    }
else:
    DEFAULT_SQLITE_PATH = Path('/tmp/db.sqlite3') if os.environ.get('VERCEL') else BASE_DIR / 'db.sqlite3'
    SQLITE_DB_PATH = env('SQLITE_DB_PATH', default=str(DEFAULT_SQLITE_PATH))

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': SQLITE_DB_PATH,
            'OPTIONS': {
                'timeout': 60,
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Internationalization
LANGUAGE_CODE = 'id-id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
if bool(os.environ.get('VERCEL', '')):
    MEDIA_ROOT = '/tmp/media'
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redis & Cache Settings
REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 300, # 5 minutes default timeout
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.cache.RedisCache',
        }
    }
}
# Fallback to dummy cache if redis is not running
try:
    import redis
    redis_conn = redis.from_url(REDIS_URL)
    redis_conn.ping()
except Exception:
    # If connection fails, fall back to LocMemCache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Celery Broker Configurations
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Fallback Celery to eager (sync) mode if redis is not running
CELERY_TASK_ALWAYS_EAGER = False
try:
    import redis
    redis_conn = redis.from_url(CELERY_BROKER_URL)
    redis_conn.ping()
except Exception:
    CELERY_TASK_ALWAYS_EAGER = True

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '1000/day',
        'auth_attempt': '5/minute', # custom rate limit for logins
    }
}

# SimpleJWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Email Backend Settings
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')

if EMAIL_HOST_USER:
    # Real SMTP — OTP emails will be delivered to real inboxes
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = env('EMAIL_PORT', cast=int, default=587)
    EMAIL_USE_TLS = env('EMAIL_USE_TLS', cast=bool, default=True)
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = f'ElectroShop <{EMAIL_HOST_USER}>'
else:
    # Console fallback — OTP codes will print in terminal
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='ElectroShop <noreply@electroshop.com>')

GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')

# ============================================
# SESSION: Cookie-based (WAJIB untuk Vercel)
# ============================================
# Di Vercel (serverless), SQLite database bersifat ephemeral.
# Session HARUS disimpan di cookie browser, bukan di database.
# Kita aktifkan ini SELALU (bukan hanya di Vercel) agar konsisten.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 hari
SESSION_COOKIE_NAME = 'electroshop_session'

# Di Vercel (HTTPS), cookie harus Secure. Di lokal (HTTP), tidak boleh Secure.
IS_VERCEL = bool(os.environ.get('VERCEL', ''))
SESSION_COOKIE_SECURE = IS_VERCEL  # True di Vercel, False di lokal
CSRF_COOKIE_SECURE = IS_VERCEL

# Message storage juga harus pakai cookie (bukan session DB)
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

# ============================================
# CSRF & Security
# ============================================
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [
    'https://electroshopone.vercel.app',
    'https://*.vercel.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
# JANGAN aktifkan SECURE_SSL_REDIRECT (Vercel sudah handle HTTPS sendiri)
SECURE_SSL_REDIRECT = False

# CORS Config
CORS_ALLOW_ALL_ORIGINS = True

# Login redirection
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'product_list'
LOGOUT_REDIRECT_URL = 'product_list'

