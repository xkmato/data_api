from django.core.management import BaseCommand
from data_api.api.tasks import fetch_all


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('api_key')

    def handle(self, api_key, *args, **options):
        fetch_all()

