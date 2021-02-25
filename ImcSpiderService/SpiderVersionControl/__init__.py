from __future__ import absolute_import, unicode_literals

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app_version as celery_app_version
from .celery import app_project as celery_app_project

__all__ = ('celery_app_version', 'celery_app_project')
