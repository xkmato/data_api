from datetime import datetime
import os
from django.conf import settings
from temba_client.v2 import TembaClient

__author__ = 'kenneth'


def get_date_from_param(param):
    if len(param) != 8:
        raise RuntimeError("Wrong date format. Use: ddmmyyyy")
    return datetime(int(param[4:8]), int(param[2:4]), int(param[:2]))


def create_folder_for_org(org_id):
    path = '%s/%s' % (settings.CSV_DUMPS_FOLDER, org_id)
    if not os.path.exists(path):
        os.makedirs(path)
        os.makedirs('%s/messages' % path)
        os.makedirs('%s/runs' % path)


def import_org(server, api_key):
    from .models import Org
    client = TembaClient(server, api_key)
    org = client.get_org()
    org_dict = org.serialize()
    org_dict['api_token'] = api_key
    org_dict['server'] = server
    local_org = Org(**org_dict)
    local_org.is_active = True
    local_org.save()
    return local_org
