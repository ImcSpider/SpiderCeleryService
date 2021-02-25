from __future__ import absolute_import
import subprocess
from SpiderVersionControl.celery import app_project
from celery.utils.log import get_task_logger
from celery.app.control import Control
from django.conf import settings

logger = get_task_logger('django')


@app_project.task(name='Start_spider_project', bind=True, max_retries=3, default_retry_delay=60)
def start_spider_project(self, platform, spider_name, store_list, username, password, company, start_id):
    pass


@app_project.task(name='Stop_spider_project', bind=True, max_retries=3, default_retry_delay=60)
def stop_spider_project(self, platform, task_id, spider_project_name, stop_id):
    pass
