from django.conf import settings
from django.db import models, transaction
from temba_client.v2 import TembaClient

from data_api.api.ingestion import RapidproAPIBaseModel

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


class OrganizationModel(models.Model, RapidproAPIBaseModel):
    organization = models.ForeignKey(Organization, db_index=True)
    first_synced = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(auto_now=True)

    rapidpro_collection = None  # should be overridden by subclasses

    class Meta:
        abstract = True

    @classmethod
    def get_collection_name(cls):
        return cls.rapidpro_collection

    @classmethod
    def object_count(cls, org):
        return cls.objects.filter(organization=org).count()

    @classmethod
    def create_from_temba(cls, org, temba, do_save=True):
        obj = cls()
        for key, value in temba.__dict__.items():
            if not hasattr(obj, key):
                continue
            print('setting {}: {}'.format(key, value))
            setattr(obj, key, value)
            # todo: going to have to deal with all these more complex data types in SQL
            # if isinstance(class_attr, ListField):
            #     item_class = class_attr.field
            #     if isinstance(item_class, EmbeddedDocumentField):
            #         item_class = item_class.document_type
            #         setattr(obj, key, item_class.instantiate_from_temba_list(getattr(temba, key)))
            #     elif isinstance(item_class, ReferenceField):
            #         # this is an opportunity to improve performance.
            #         # rather than querying our local DB for the object and using a ReferenceField,
            #         # we could instead just set an ID on the current document and not bother with
            #         # doing explicit mongo references.
            #         # this would avoid a huge number of DB lookups.
            #         # An alternative option would be to just cache the result of this call
            #         # so that multiple queries, e.g. to the same Contact, resolve quickly.
            #         # Caching might introduce complex invalidation logic - e.g. if a model was imported
            #         # midway through a full import.
            #         uuids = [v.uuid for v in getattr(temba, key)]
            #         setattr(obj, key, item_class.document_type.get_objects_from_uuids(org, uuids))
            #     else:
            #         setattr(obj, key, value)
            # elif isinstance(class_attr, MapField):
            #     item_class = class_attr.field
            #     assert isinstance(item_class, EmbeddedDocumentField)
            #     setattr(obj, key, {
            #         k: item_class.document_type.instantiate_from_temba(v) for k, v in getattr(temba, key).items()
            #     })
            #
            # elif isinstance(class_attr, ReferenceField) and getattr(temba, key) is not None:
            #     item_class = class_attr.document_type
            #     # same note applies as above on the list version
            #     setattr(obj, key, item_class.get_or_fetch(org, getattr(temba, key).uuid))
            # elif isinstance(class_attr, EmbeddedDocumentField):
            #     item_class = class_attr.document_type
            #     setattr(obj, key, item_class.instantiate_from_temba(getattr(temba, key)))

        obj.organization = org
        if do_save:
            obj.save()
        return obj

    @classmethod
    def bulk_save(cls, chunk_to_save):
        with transaction.atomic():
            for obj in chunk_to_save:
                obj.save()


class Group(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100)
    query = models.CharField(max_length=100, null=True, blank=True)
    count = models.IntegerField()

    rapidpro_collection = 'groups'
