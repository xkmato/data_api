from django.core.management import BaseCommand
from temba_client.v2 import TembaClient
from data_api.api.models import Org

class Command(BaseCommand):

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('api_key')

        # Named (optional) arguments
        parser.add_argument(
            '--server',
            action='store',
            dest='server',
            default='https://rapidpro.io',
            help='Bootstrap an org from an API key',
        )

    def handle(self, api_key, server, *args, **options):
        print('server: {}, api key: {}'.format(server, api_key))
        client = TembaClient(server, api_key)
        org = client.get_org()
        org_dict = org.serialize()
        org_dict['api_token'] = api_key
        local_org = Org(**org_dict)
        local_org.save()



