from __future__ import absolute_import
import subprocess
from SpiderVersionControl.celery import app_version
from celery.utils.log import get_task_logger
from celery.app.control import Control
from django.conf import settings

logger = get_task_logger('Celery')


@app_version.task(name='Finance_service', bind=True, max_retries=3, default_retry_delay=60)
def finance_service(self, platform, *args, **kwargs):
    pass

