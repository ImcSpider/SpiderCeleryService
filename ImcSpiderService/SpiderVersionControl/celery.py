# celery配置
from __future__ import absolute_import, unicode_literals
import os
import django
from celery import Celery
from django.conf import global_settings
from django.conf import settings

# 设置celery执行的环境变量，执行django项目的配置文件
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SpiderVersionControl.settings')

django.setup()

# 创建celery应用(版本控制)
app_version = Celery('spider_version_control', broker=settings.CELERY_TASK_APP_BROKER,
                     backend=settings.CELERY_TASK_APP_BACKEND)  # celery应用的名称
app_version.config_from_object('SpiderVersionControl.settings', force=True)  # 加载的配置文件
# 创建celery应用(项目控制)
app_project = Celery('spider_project_control', broker=settings.PROJECT_TASK_APP_BROKER,
                     backend=settings.PROJECT_TASK_APP_BACKEND)  # celery应用的名称
app_project.config_from_object('SpiderVersionControl.settings', force=True)  # 加载的配置文件

# 如果在工程的应用中创建了task.py模块，那么Celery应用就会自动去检测创建的任务，
# 比如你添加一个任务，在django中会实时的检测出来。
app_version.autodiscover_tasks(lambda: global_settings.INSTALLED_APPS)
app_project.autodiscover_tasks(lambda: global_settings.INSTALLED_APPS)
