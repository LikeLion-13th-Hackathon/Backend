from pathlib import Path

import pymysql
pymysql.install_as_MySQLdb()

import os, json
from django.core.exceptions import ImproperlyConfigured

from datetime import timedelta #login

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# secret_key setting
secret_file = os.path.join(BASE_DIR, 'secrets.json') 

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets): 
# secret 변수를 가져오거나 그렇지 못 하면 예외를 반환
    try:
        return secrets[setting]
    except KeyError:
        error_msg = "Set the {} environment variable".format(setting)
        raise ImproperlyConfigured(error_msg)


ENV = os.getenv('ENV', 'local')  # 기본값은 'local'
    
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [   # 프론트 배포 후 백엔드 도메인으로 변경 
    '127.0.0.1',
    'localhost',
    'ec2-54-180-214-201.ap-northeast-2.compute.amazonaws.com',  # 퍼블릭 DNS
    '54.180.214.201',   # 퍼블릭 IPv4
    'oyes-hackathon.o-r.kr', # gpt 가 해보래!
    'www.oyes-hackathon.o-r.kr',  # 필요하면 www 도 추가
]


# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

PROJECT_APPS = [
    'testapi',
    'accounts',
    'receipts',
    'stores',
    'markets',
    'menu',
    'ai',
    "reviews",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    'rest_framework_simplejwt',
    'storages',
]

INSTALLED_APPS = DJANGO_APPS + PROJECT_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # "allauth.account.middleware.AccountMiddleware",
]

# CSRF_TRUSTED_ORIGINS = [
#     'https://oyes-hackathon.o-r.kr'
# ]

ALLOWED_ORIGINS = [    
    'https://oyes-hackathon.o-r.kr'
]
CSRF_TRUSTED_ORIGINS = ALLOWED_ORIGINS.copy()

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DB_NAME = get_secret("DB_NAME")
DB_PW = get_secret("DB_PW")

USER = get_secret("USER")
HOST = get_secret("HOST") # 로컬 테스트할 땐 'localhost'로 변경
PORT = get_secret("PORT")

# 로컬 테스트, SSH 터널링, AWS RDS 연결 바꿀 때마다 settings.py의 DB_NAME, USER, DB_PW, HOST, PORT 변경 필요
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME,
        'USER': USER,
        'PASSWORD': DB_PW,
        'HOST': HOST,
        'PORT': PORT,
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECRET_KEY = get_secret("SECRET_KEY")

CORS_ALLOW_CREDENTIALS = True   

CORS_ALLOWED_ORIGINS = [    # 프론트 배포 후 프론트 도메인으로 변경
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173", # 프론트 - 권민정
    "http://oyes-hackathon.o-r.kr",
    "https://oyes-hackathon.o-r.kr"
]

### LOGIN ###

AUTH_USER_MODEL = 'accounts.User' #accounts

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

REST_USE_JWT = True

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=20),    # 유효기간 3시간 (개발 기간동안 프론트 접근 가능하도록 임의로 20일)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),    # 유효기간 7일
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'TOKEN_USER_CLASS': 'accounts.User',
    'USER_ID_FIELD': 'user_id',
    'USER_ID_CLAIM': 'user_id',
}

# AWS
AWS_ACCESS_KEY_ID = get_secret("AWS_ACCESS_KEY_ID") # .csv 파일에 있는 내용을 입력 Access key ID. IAM 계정 관련
AWS_SECRET_ACCESS_KEY = get_secret("AWS_SECRET_ACCESS_KEY") # .csv 파일에 있는 내용을 입력 Secret access key. IAM 계정 관련
AWS_REGION = 'ap-northeast-2'

# S3
AWS_STORAGE_BUCKET_NAME = 'oyes-hackathon'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.%s.amazonaws.com' % (AWS_STORAGE_BUCKET_NAME,AWS_REGION)
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

X_OCR_SECRET = get_secret("X_OCR_SECRET")

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")