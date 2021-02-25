import redis
import json
import os
import datetime
import time
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
            try:
                start_id = request.POST["ID"].strip()
                platform = request.POST["Platform"].strip().lower()
                spider_name = request.POST["CrawlType"].strip()
                store_list_str = request.POST['StoreAccountList']
                store_list = json.dumps(store_list_str.split(','))
                company = request.POST['CompanyName'].strip()
                username = request.POST["Account"].strip()
                password = request.POST["PassWord"].strip()
            except KeyError:
                result_msg = {"Message": "启动失败：参数名错误.", "ID": start_id, "Status": 2, "Success": "false"}
                return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                    charset="utf-8")
            logger.info("用户传输信息:%s - %s - %s - %s - %s" % (platform, spider_name, company, store_list[:10], username))
            # 判断平台是否存在
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
            # 清除对应平台的redis队列信息
            clear_redis_queue(platform)
            # 清除所有队列信息
            # control = Control(app)
            # msg = control.purge()
            global res
            global result
            if platform == 'amazon':
                # 调用worker
                res = start_spider_project.apply_async(
                    args=[spider_name, store_list, username, password, company, start_id],
                    queue='amazon',
                    routing_key='amazon.finace')
                spider_project_task_dic[spider_name] = res.id
                result = res.get()
            else:
                result = {"Message": "启动失败：不存在 %s 平台." % platform, "ID": start_id, "Status": 2, "Success": "false"}
            return HttpResponse(json.dumps(result, ensure_ascii=False), content_type="application/json",
                                charset="utf-8")

        elif type_ == "stop":
            try:
                stop_id = request.POST["ID"]
                platform_name = request.POST["Platform"].strip().lower()
                spider_project_name = request.POST["CrawlType"]
            except KeyError:
                result_msg = {"Message": "终止失败：参数名错误.", "ID": stop_id, "Status": 7, "Success": "false"}
                return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                    charset="utf-8")
            if platform_name.strip() in settings.SPIDER_PLATFORM:
                queue_name = platform_name.strip()
                try:
                    task_id = spider_project_task_dic[spider_project_name]
                except KeyError:
                    result_msg = {"Message": "此 %s 爬虫未在运行中...请检查后重试..." % spider_project_name, "ID": stop_id,
                                  "Status": 7, "Success": "false"}
                    return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                        charset="utf-8")
                response = stop_spider_project.apply_async(args=[task_id, spider_project_name, stop_id],
                                                           queue=queue_name,
                                                           routing_key=queue_name)
                stop_timeout = 20
                while stop_timeout:
                    stop_timeout -= 1
                    if response.successful():
                        # print(response.state)
                        # print(response.result)
                        # print(response.get())
                        result_msg = response.get()
                        spider_project_task_dic.pop(spider_project_name)
                        return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                            charset="utf-8")
                    time.sleep(1)
                result_msg = {"Message": "手动终止 %s 超时...请重试..." % spider_project_name, "ID": stop_id,
                              "Status": 7, "Success": "false"}
                return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                    charset="utf-8")

            else:
                result_msg = {"Message": "此平台  %s 不存在...请重试..." % platform_name, "ID": stop_id,
                              "Status": 7, "Success": "false"}
                return HttpResponse(json.dumps(result_msg, ensure_ascii=False), content_type="application/json",
                                    charset="utf-8")
        else:
            msg = {"Message": "ExecuteType 参数非法!", "ID": stop_id, "Status": 7, "Success": "false"}
            return HttpResponse(json.dumps(msg, ensure_ascii=False), content_type="application/json", charset="utf-8")
    else:
        msg = {"Message": "不接收GET请求!", "ID": stop_id, "Status": 7, "Success": "false"}
        return HttpResponse(json.dumps(msg, ensure_ascii=False), content_type="application/json", charset="utf-8")
