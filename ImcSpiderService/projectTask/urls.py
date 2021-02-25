from django.conf.urls import url
from . import views

urlpatterns = [
    # 用户传输启动信息调用爬虫接口# 主动终止爬虫任务
    url(r'^Finance', views.platform_link),
]
