from django.core.management import BaseCommand
from django.utils import six

from data_api.staging.models import Organization, OrganizationModel


class Command(BaseCommand):

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('org_id')
        parser.add_argument(
            '--noinput',
            action='store_true',
            dest='noinput',
            default=False,
            help='No prompts will be shown to user.',
        )

    def handle(self, org_id, *args, **options):

        try:
            org = Organization.objects.get(id=org_id)
        except (ValueError, Organization.DoesNotExist):
            # try by api token
            org = Organization.objects.get(api_token=org_id)
        org_models = OrganizationModel.__subclasses__()
        noinput = options['noinput']
        if noinput:
            print('Deleting the following models:')
        else:
            print('Are you sure you want to delete this organization: {} ({}) including the following models?'.format(
                org.name, org.id
            ))

        for model in org_models:
            print('  {} {}s'.format(model.objects.filter(organization=org).count(), model.__name__))

        if noinput or six.moves.input('y/N: ').lower().strip() == 'y':
            org.delete()
            print('org {} was deleted.'.format(org.name))
        else:
            print('deletion canceled by user')
