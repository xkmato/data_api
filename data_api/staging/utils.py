from .models import Organization


def import_org_with_client(client, server, api_key):
    org = client.get_org()
    org_dict = org.serialize()
    org_dict['api_token'] = api_key
    org_dict['server'] = server
    org_dict['is_active'] = True
    try:
        local_org = Organization.objects.get(api_token=api_key)
        for k, v in org_dict.iteritems():
            setattr(local_org, k, v)
        local_org.save()
        return local_org
    except Organization.DoesNotExist:
        return Organization.objects.create(**org_dict)
