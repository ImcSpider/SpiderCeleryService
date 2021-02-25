import redis
import json
import os
import datetime
import time
import eventlet
import logging
import ast
import signal
from projectTask.tasks import start_spider_project, stop_spider_project
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from celery.app.control import Control
from celery.concurrency import base
from celery.result import AsyncResult

logger = logging.getLogger('django')
redis_pool = redis.ConnectionPool(host=settings.REDIS_IP, port=settings.REDIS_PORT,
                                  db=settings.PROJECT_CONTROL_REDIS_DB)
redis_db = redis.Redis(connection_pool=redis_pool)

spider_project_task_dic = {}
response_platform_dic = {}


# 清除当前队列信息
def clear_redis_queue(key):
    redis_db.ltrim(key, 0, 0)
    redis_db.lpop(key)


def clear_log_files():
    log_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'logs')
    file_name_list = os.listdir(log_path)
    if len(file_name_list) > 30:
        for file_name in file_name_list:
            try:
                try:
                    os.remove(os.path.join(log_path, file_name))
                except Exception as e:
                    logger.error("projectTask app line 39 error: %s " % e)
                    with open(os.path.join(log_path, file_name), 'a', encoding='utf-8') as fp:
                        fp.seek(0)
                        fp.truncate()
            except Exception as e:
                logger.error("projectTask app line 46 error: %s " % e)
        logger.info("clear logs success.")


def start_project(request):
    global start_id
    try:
        start_id = request.POST["ID"].strip()
        platform_str = request.POST["Platform"].strip().lower()
        platform_list = [name.strip() for name in platform_str.split(',')]
        if not platform_list:
            raise KeyError("platform 不能为空.")
        spider_name = request.POST["CrawlType"].strip()
        store_list_str = request.POST['StoreAccountList']
        store_list = json.dumps(store_list_str.split(','))
        company = request.POST['CompanyName'].strip()
        username = request.POST["Account"].strip()
        password = request.POST["PassWord"].strip()
    except KeyError:
        result_msg = {"Message": "启动失败：参数名错误/参数不能为空.", "ID": start_id, "Status": 2, "Success": "false"}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")

    logger.info(
        "用户传输信息:%s - %s - %s - %s - %s" % (platform_str, spider_name, company, store_list[:10], username))
    # 判断平台是否存在
    for platform in platform_list:
        if platform not in settings.SPIDER_PLATFORM:
            result_msg = {"Message": "启动失败：此平台  %s 不存在...请重试..." % platform, "ID": start_id, "Status": 2,
                          "Success": "false"}
            return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                charset="utf-8")
    # 验证账号密码是否存在不为空
    if not username or not company or not password or not spider_name:
        result_msg = {"Message": "启动失败：参数不能为空.", "ID": start_id, "Status": 2, "Success": "false"}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")
    # 验证store_list的类型是否正确并判断是否为空
    if not isinstance(json.loads(store_list), list) or len(json.loads(store_list)) == 0:
        result_msg = {"Message": "启动失败：店铺列表类型错误或者列表为空.", "ID": start_id, "Status": 2, "Success": "false"}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")
    # 清除所有队列信息
    # control = Control(app)
    # msg = control.purge()
    # 清除对应平台的redis队列信息
    for platform in platform_list:
        clear_redis_queue(platform)
        # 调用worker
        res = start_spider_project.apply_async(
            args=[platform, spider_name, store_list, username, password, company, start_id], queue=platform,
            routing_key=platform)
        key = '_'.join([platform, spider_name])
        spider_project_task_dic[key] = res.id
        response_platform_dic[key] = res

    # 等待各虚拟机反馈启动项目是否成功
    response_backend = list()
    for key, value in response_platform_dic.items():
        result = value.get()
        response_backend.append(result)
    return HttpResponse(json.dumps(response_backend, ensure_ascii=False), content_type="application/json",
                        charset="utf-8")


def stop_project(request):
    global stop_id
    global response_backend_
    try:
        stop_id = request.POST["ID"]
        platform_name = request.POST["Platform"].strip().lower()
        platform_list = [name.strip() for name in platform_name.split(',')]
        if not platform_list:
            raise KeyError("platform 不能为空.")
        for platform in platform_list:
            if platform not in settings.SPIDER_PLATFORM:
                raise KeyError(" %s 虚拟机不存在." % platform)
        spider_project_name = request.POST["CrawlType"]
    except KeyError:
        result_msg = {"Message": "终止失败：参数名/参数错误.", "ID": stop_id, "Status": 7, "Success": "false"}
        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                            charset="utf-8")
    response_backend_ = list()
    green_thread_pool = eventlet.GreenPool()
    for platform in platform_list:
        clear_redis_queue(platform)
        key = '_'.join([platform, spider_project_name])
        try:
            task_id = spider_project_task_dic[key]
        except KeyError:
            result_msg = {"Message": "此 %s 爬虫未在 %s 虚拟机运行.请检查后重试." % (spider_project_name, platform),
                          "ID": stop_id, "Status": 7, "Success": "false"}
            return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                charset="utf-8")
        response = stop_spider_project.apply_async(args=[platform, task_id, spider_project_name, stop_id],
                                                   queue=platform,
                                                   routing_key=platform)
        green_thread_pool.spawn(wait_stop_response, args=(response, key, platform, spider_project_name))
    green_thread_pool.waitall()
    logger.info('%s ========' % response_backend_)
    return HttpResponse(json.dumps(response_backend_, ensure_ascii=False), content_type="application/json",
                        charset="utf-8")


def wait_stop_response(response, key, platform, spider_project_name):
    global response_backend_
    stop_timeout = 20
    while stop_timeout:
        stop_timeout -= 1
        if response.successful():
            # print(response.state)
            # print(response.result)
            # print(response.get())
            result_msg = response.get()
            spider_project_task_dic.pop(key)
            response_backend_.append(result_msg)
            break
        time.sleep(1)
    if stop_timeout == 0:
        result_msg = {"Message": "手动终止虚拟机 %s 下项目 %s 超时.请重试." % (platform, spider_project_name),
                      "ID": stop_id, "Status": 7, "Success": "false"}
        response_backend_.append(result_msg)


@csrf_exempt
def platform_link(request):
    global start_id
    global stop_id
    global type_
    start_id = ""
    stop_id = ""
    if request.method == 'POST':
        # 日志清除
        clear_log_files()
        # 判断是启动还是停止
        try:
            type_ = request.POST["ExecuteType"].strip().lower()
        except KeyError:
            result_msg = {"Message": "启动失败：缺少ExecuteType参数.", "ID": start_id, "Status": 2, "Success": "false"}
            return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                charset="utf-8")
        if type_ == "start":
            content = start_project(request)
        elif type_ == "stop":
            content = stop_project(request)
        else:
            content = {"Message": "ExecuteType 参数非法!", "ID": stop_id, "Status": 7, "Success": "false"}
        return HttpResponse(json.dumps(content, ensure_ascii=False), content_type="application/json", charset="utf-8")
    else:
        msg = {"Message": "不接收GET请求!", "ID": stop_id, "Status": 7, "Success": "false"}
        return HttpResponse(json.dumps(msg, ensure_ascii=False), content_type="application/json", charset="utf-8")
