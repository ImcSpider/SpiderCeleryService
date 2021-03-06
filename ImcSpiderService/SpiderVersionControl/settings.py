"""
Django settings for SpiderVersionControl project.

Generated by 'django-admin startproject' using Django 1.11.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import time
import djcelery
from kombu import Exchange, Queue

# redis地址
REDIS_IP = '127.0.0.1'
REDIS_PORT = 6379
VERSION_CONTROL_REDIS_DB = 10
PROJECT_CONTROL_REDIS_DB = 8

# 版本控制应用
PROJECT_TASK_APP_BROKER = "redis://127.0.0.1:6379/8"
PROJECT_TASK_APP_BACKEND = "redis://127.0.0.1:6379/9"
# 爬虫项目应用
CELERY_TASK_APP_BROKER = "redis://127.0.0.1:6379/10"
CELERY_TASK_APP_BACKEND = "redis://127.0.0.1:6379/11"

# 存在虚拟机列表
SPIDER_PLATFORM = ['finance_service_1', 'finance_service_2', 'finance_service_3', 'finance_service_4',
                   'finance_service_5', 'finance_service_6', 'finance_service_7', 'finance_service_8',
                   'finance_service_9', 'finance_service_10'
                   ]

# 加载celery
djcelery.setup_loader()
# 消息队列
# broker_url = 'redis://127.0.0.1:6379/8'
# BROKER_URL = "redis://127.0.0.1:6379/10"
# result_backend = 'redis://127.0.0.1:6379/9'
# CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/11"
# imports = ('celeryTask.tasks')
CELERY_IMPORTS = ('celeryTask.tasks', 'projectTask.tasks')
# timezone = 'Asia/Shanghai'
CELERY_TIMEZONE = 'Asia/Shanghai'
# task_track_started = True
CELERY_TRACK_STARTED = True
# beat_scheduler = 'djcelery.schedulers.DatabaseScheduler'
# 定义一个默认交换机
# default_exchange = Exchange('finaceSpider', type='direct')

CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
CELERYD_CONCURRENCY = 20
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600, 'fanout_prefix': True, 'fanout_patterns': True}
# 创建队列
CELERY_QUEUES = [
    Queue('default', routing_key='default'),
    Queue('finance_service_1', routing_key='finance_service_1'),
    Queue('finance_service_2', routing_key='finance_service_2'),
    Queue('finance_service_3', routing_key='finance_service_3'),
    Queue('finance_service_4', routing_key='finance_service_4'),
    Queue('finance_service_5', routing_key='finance_service_5'),
    Queue('finance_service_6', routing_key='finance_service_6'),
    Queue('finance_service_7', routing_key='finance_service_7'),
    Queue('finance_service_8', routing_key='finance_service_8'),
    Queue('finance_service_9', routing_key='finance_service_9'),
    Queue('finance_service_10', routing_key='finance_service_10')
]

# task_default_queue = 'default'
CELERY_DEFAULT_QUEUE = 'default'
# task_default_exchange = 'celery'
CELERY_DEFAULT_EXCHANGE = 'default'
# task_default_routing_key = 'default'
CELERY_DEFAULT_ROUTING_KEY = 'default'

CELERY_ROUTES = ({
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_1',
                         'routing_key': 'finance_service_1'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_2',
                         'routing_key': 'finance_service_2'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_3',
                         'routing_key': 'finance_service_3'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_4',
                         'routing_key': 'finance_service_4'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_5',
                         'routing_key': 'finance_service'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_6',
                         'routing_key': 'finance_service_6'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_7',
                         'routing_key': 'finance_service_7'}},
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_8',
                         'routing_key': 'finance_service_8'}
                 },
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_9',
                         'routing_key': 'finance_service_9'}
                 },
                 {
                     'celeryTask.tasks.finance_service': {
                         'queue': 'finance_service_10',
                         'routing_key': 'finance_service_10'}
                 }
)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ml$1w_$6_mte0y2=v!(+5=xnwz^c2tlze0iz76we!_vkgtq9l)'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djcelery',
    'celeryTask',
    'projectTask',
    'rest_framework'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'SpiderVersionControl.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SpiderVersionControl.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, '/static/')]
STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'static')

# 日志配置
cur_path = os.path.dirname(os.path.realpath(__file__))  # log_path是存放日志的路径
log_path = os.path.join(os.path.dirname(cur_path), 'logs')
if not os.path.exists(log_path):
    os.mkdir(log_path)  # 如果不存在这个logs文件夹，就自动创建一个

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        # 日志格式
        'standard': {
            'format': '[%(asctime)s] [%(filename)s:%(lineno)d] [%(module)s:%(funcName)s] '
                      '[%(levelname)s]- %(message)s'},
        'simple': {  # 简单格式
            'format': '%(levelname)s %(message)s'
        },
    },
    # 过滤
    'filters': {
    },
    # 定义具体处理日志的方式
    'handlers': {
        # 默认记录所有日志
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'django_all-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 50,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码，否则打印出来汉字乱码
        },
        # 版本控制应用日志
        'celery': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'django_celery_version_control.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 50,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码，否则打印出来汉字乱码
        },
        # 输出错误日志
        'error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'django_error-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 50,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码
        },
        # 控制台输出
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        # 输出info日志
        'info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'django_info-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',  # 设置默认编码
        },
    },
    # 配置用哪几种 handlers 来处理日志
    'loggers': {
        # 类型 为 django 处理所有类型的日志， 默认调用
        'django': {
            'handlers': ['default', 'console'],
            'level': 'INFO',
            'propagate': False
        },
        # log 调用时需要当作参数传入
        'log': {
            'handlers': ['error', 'console', 'default'],
            'level': 'INFO',
            'propagate': True
        },
        # celery 调用时
        'celery': {
            'handlers': ['celery', 'console'],
            'level': 'INFO',
            'propagate': True
        },
    }
}
