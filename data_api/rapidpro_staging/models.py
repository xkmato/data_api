from django.conf import settings
from django.db import models
from temba_client.v2 import TembaClient

"""
RapidPro Staging SQL models live here. The word "staging" comes from the data warehouse 
notion of staging where the raw data from an external system is staged as-is in the warehouse.
Thus, these models represent the *raw* rapidpro data.

It is anticipated that there might one day be a "rapidpro_warehouse" app that aggregates/denormalizes
the staging data in a way to make data warehouse operations more efficient. 

Eventually this will replace the mongo models in api.models, but for the transition period
the intention is to have two models files, one for mongo and one for SQL.
"""


class Organization(models.Model):
    api_token = models.CharField(max_length=32)
    server = models.CharField(max_length=100, default=settings.DEFAULT_RAPIDPRO_SITE)
    is_active = models.BooleanField(default=False)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, null=True, blank=True)
    primary_language = models.CharField(max_length=100)
    timezone = models.CharField(max_length=100, null=True, blank=True)
    date_style = models.CharField(max_length=100, null=True, blank=True)
    anon = models.BooleanField(default=False)

    # todo: need a plan for lists and dicts. JSONField?
    UNMIGRATED_FIELDS = ['languages', 'credits']
    # languages = ListField(StringField())
    # credits = DictField()

    meta = {'collection': 'orgs'}

    def get_temba_client(self):
        return TembaClient(self.server, self.api_token)

    def __unicode__(self):
        return self.name

    # def get_runs(self):
    #     return Run.objects.filter(org__id=self.id)
    #
    # def get_contacts(self):
    #     return Contact.objects.filter(org__id=self.id)
    #
    # def get_flows(self):
    #     return Flow.objects.filter(org__id=self.id)


