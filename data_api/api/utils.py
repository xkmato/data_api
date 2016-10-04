from datetime import datetime
import os
from django.conf import settings

__author__ = 'kenneth'


def get_date_from_param(param):
    if len(param) != 8:
        raise RuntimeError("Wrong date format. Use: ddmmyyyy")
    return datetime(int(param[4:8]), int(param[2:4]), int(param[:2]))


def create_folder_for_org(org_id):
    path = '%s/%s' % (settings.CSV_DUMPS_FOLDER, org_id)
    if not os.path.exists(path):
        os.makedirs(path)