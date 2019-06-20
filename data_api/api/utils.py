from mongoengine import DoesNotExist
from temba_client.v2 import TembaClient

__author__ = 'kenneth'


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
