from django.core.management import BaseCommand
from temba_client.v2 import TembaClient
from data_api.api.models import Org, OrgDocument, LastSaved
from data_api.api.utils import import_org


class Command(BaseCommand):

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('org_id')

    def handle(self, org_id, *args, **options):
        org = Org.objects.get(**{'id': org_id})
        org_models = OrgDocument.__subclasses__()
        print('Are you sure you want to delete this organization: {} ({}) including the following models?'.format(
            org.name, org.id
        ))

        for model in org_models:
            print('  {} {}s'.format(model.objects.filter(org_id=org.id).count(), model.__name__))
        if raw_input('y/N: ').lower().strip() == 'y':
            for model in org_models:
                model.objects.filter(org_id=org.id).delete()
            LastSaved.objects.filter(org=org).delete()
            org.delete()
            print('org {} was deleted.'.format(org.name))
        else:
            print('deletion canceled by user')
