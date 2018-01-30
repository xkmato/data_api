from datetime import datetime
import os
from django.conf import settings
from mongoengine import DoesNotExist
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
    client = TembaClient(server, api_key)
    return import_org_with_client(client, server, api_key)


def import_org_with_client(client, server, api_key):
    # the main reason for this method existing is so the client can be easily mocked in tests
    from .models import Org
    org = client.get_org()
    org_dict = org.serialize()
    org_dict['api_token'] = api_key
    org_dict['server'] = server
    org_dict['is_active'] = True
    try:
        local_org = Org.objects.get(**{'api_token': api_key})
        local_org.update(**org_dict)
        return Org.objects.get(**{'api_token': api_key})
    except DoesNotExist:
        local_org = Org(**org_dict)
        local_org.save()
    return local_org
