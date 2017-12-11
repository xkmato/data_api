from __future__ import absolute_import, unicode_literals

import os
from celery import Celery

__author__ = 'kenneth'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_api.settings')

app = Celery('data_api')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
