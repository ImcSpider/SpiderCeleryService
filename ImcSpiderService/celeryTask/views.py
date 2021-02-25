import redis
import time
import logging
import json
import re
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .tasks import finance_service

logger = logging.getLogger('celery')
redis_pool = redis.ConnectionPool(host=settings.REDIS_IP, port=settings.REDIS_PORT,
                                  db=settings.VERSION_CONTROL_REDIS_DB)
redis_db = redis.Redis(connection_pool=redis_pool)

spider_project_task_dic = {}


# 清除当前队列信息
def clear_redis_queue(key):
    redis_db.ltrim(key, 0, 0)
    redis_db.lpop(key)


# Create your views here.

@csrf_exempt
def version_control(request):
    '''版本控制更新：
        total为1 则更新所有虚拟机上的项目,
        total为0 则更新指定虚拟机上项目
    '''
    global total_flag
    current_url = request.get_full_path()
    try:
        total_flag = int(re.findall(r'.*?total=(\d+)', current_url)[0])
    except IndexError:
        result_msg = {"error": "此url缺少关键参数total."}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")
    try:
        if total_flag:
            service_platform_list = settings.SPIDER_PLATFORM
        else:
            service_platform_string = re.findall(r'.*?platform=\[(.*)\]', current_url)[0]
            service_platform_list = service_platform_string.split(',')
            if not service_platform_list:
                raise IndexError
            for platform in service_platform_list:
                if platform not in settings.SPIDER_PLATFORM:
                    raise IndexError('%s 此虚拟机不存在.' % platform)
    except IndexError:
        result_msg = {"error": "此url缺少关键参数platform或者platform参数错误."}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")
    response_platform_dic = dict()
    logger.info("准备唤醒虚拟机列表 : %s " % service_platform_list)
    try:
        for platform in service_platform_list:
            clear_redis_queue(platform)
            res = finance_service.apply_async(args=[platform], queue=platform, routing_key=platform)
            spider_project_task_dic[platform] = res.id
            response_platform_dic[platform] = res

        for key, res in response_platform_dic.items():
            result = json.loads(res.get())
            return HttpResponse(json.dumps(result, ensure_ascii=False), content_type="application/json",
                                charset="utf-8")
    except Exception as e:
        logging.error("执行更新项目方法时发生错误. ErrorMsg : %s" % e)
        result_msg = {"error": "执行更新项目方法时发生错误. ErrorMsg : %s" % e}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")
    result_msg = {"success": True, "message": "%s 项目更新完成." % service_platform_list}
    return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                        charset="utf-8")
