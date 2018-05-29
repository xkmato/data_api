from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
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


class SyncCheckpoint(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    collection_name = models.CharField(max_length=100)
    subcollection_name = models.CharField(max_length=100, null=True, blank=True)
    last_started = models.DateTimeField()
    last_saved = models.DateTimeField(null=True, blank=True)
    is_running = models.BooleanField(default=False)

    class Meta:
        unique_together = ('organization', 'collection_name', 'subcollection_name')


class RapidproCreateableModelMixin(object):
    """
    This mixin is for anything that can be created from a rapidpro temba api object,
    including base models and embedded/foreign-key models.
    """

    @classmethod
    def create_from_temba(cls, org, temba, do_save=True):
        obj = cls()
        # will map field names to lists of fields to add, since all related models and the primary
        # need to be saved before we can save the relationship information
        related_models = {}
        for key, temba_value in temba.__dict__.items():
            warehouse_attr = get_warehouse_attr_for_rapidpro_key(key)
            try:
                field = cls._meta.get_field(warehouse_attr)
            except FieldDoesNotExist:
                continue

            if isinstance(field, models.OneToOneField) and temba_value is not None:
                # we have to save related models in django
                setattr(obj, warehouse_attr, field.related_model.create_from_temba(org, temba_value, do_save=True))
            elif isinstance(field, models.ForeignKey) and temba_value is not None:
                # this is an opportunity to improve performance.
                # rather than querying our local DB for the object and using a ForeignKey,
                # we could instead just set an ID on the current document and not bother with
                # doing explicit foreign key references.
                # this would avoid a huge number of DB lookups.
                # An alternative option would be to just cache the result of this call
                # so that multiple queries, e.g. to the same Contact, resolve quickly.
                # Caching might introduce complex invalidation logic - e.g. if a model was imported
                # midway through a full import.
                setattr(obj, warehouse_attr, field.related_model.objects.get(uuid=temba_value.uuid))
            elif isinstance(field, models.ManyToManyField) and temba_value is not None:
                assert isinstance(temba_value, list)
                warehouse_models = []
                for nested_object in temba_value:
                    try:
                        warehouse_object = field.related_model.objects.get(uuid=nested_object.uuid)
                    except field.related_model.DoesNotExist:
                        warehouse_object = field.related_model.create_from_temba(org, nested_object, do_save=True)
                    warehouse_models.append(warehouse_object)
                related_models[warehouse_attr] = warehouse_models
            else:
                setattr(obj, warehouse_attr, temba_value)
            # todo: going to have to deal with all these more complex data types in SQL
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
        if do_save or related_models:
            obj.save()
            for attr, related_objs in related_models.iteritems():
                for related_obj in related_objs:
                    getattr(obj, attr).add(related_obj)
        return obj


class RapidproBaseModel(models.Model, RapidproCreateableModelMixin):
    class Meta:
        abstract = True


class OrganizationModel(RapidproBaseModel, RapidproAPIBaseModel):
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


class Contact(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100, null=True, blank=True)
    language = models.CharField(max_length=100, null=True, blank=True)
    # todo
    # urns = ListField(EmbeddedDocumentField(Urn))
    groups = models.ManyToManyField(Group, null=True)
    # todo
    # fields = DictField()
    blocked = models.NullBooleanField()
    stopped = models.NullBooleanField()
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField()

    rapidpro_collection = 'contacts'


class Field(OrganizationModel):
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    value_type = models.CharField(max_length=100)

    rapidpro_collection = 'fields'


class Device(RapidproBaseModel):
    power_status = models.CharField(max_length=100)
    power_source = models.CharField(max_length=100)
    power_level = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    network_type = models.CharField(max_length=100)


class Channel(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    device = models.OneToOneField(Device, null=True, blank=True)
    last_seen = models.DateTimeField()
    created_on = models.DateTimeField()

    rapidpro_collection = 'channels'


class ChannelEvent(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    type = models.CharField(max_length=100)
    contact = models.ForeignKey(Contact)
    channel = models.ForeignKey(Channel)
    # todo:
    # extra = DictField()
    occurred_on = models.DateTimeField()
    created_on = models.DateTimeField()

    rapidpro_collection = 'channel_events'


class Broadcast(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    # todo figure out Urns
    # urns = models.ManyToManyField(Urn)
    contacts = models.ManyToManyField(Contact)
    groups = models.ManyToManyField(Group)
    text = models.TextField()  # todo: this might need to also support dicts
    created_on = models.DateTimeField()

    rapidpro_collection = 'broadcasts'

    def __unicode__(self):
        return "{}".format(self.text)


class Campaign(OrganizationModel):
    uuid = models.UUIDField()
    group = models.ForeignKey(Group)
    archived = models.BooleanField(default=False)
    created_on = models.DateTimeField()
    name = models.CharField(max_length=100)

    rapidpro_collection = 'campaigns'


class Label(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100)
    count = models.IntegerField()

    rapidpro_collection = 'labels'


class Runs(RapidproBaseModel):
    active = models.IntegerField(default=0)
    completed = models.IntegerField(default=0)
    expired = models.IntegerField(default=0)
    interrupted = models.IntegerField(default=0)


class Flow(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100)
    archived = models.BooleanField(default=False)
    # labels = models.ManyToManyField(Label)  # todo
    expires = models.IntegerField()
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField(null=True, blank=True)
    runs = models.OneToOneField(Runs)

    rapidpro_collection = 'flows'

    # todo
    # def get_runs(self, queryset=None):
    #     if queryset:
    #         return queryset.filter(flow=self)
    #     return Run.objects.filter(flow__id=self.id)


class FlowStart(OrganizationModel):
    uuid = models.UUIDField()
    flow = models.ForeignKey(Flow)
    groups = models.ManyToManyField(Group)
    contacts = models.ManyToManyField(Contact)
    restart_participants = models.BooleanField()
    status = models.CharField(max_length=100)
    # todo
    # extra = DictField()
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField()

    rapidpro_collection = 'flow_starts'
    UNMIGRATED_FIELDS = ['extra']


class CampaignEvent(OrganizationModel):
    uuid = models.UUIDField()
    campaign = models.ForeignKey(Campaign)
    # relative_to = EmbeddedDocumentField(FieldRef)
    offset = models.IntegerField()
    unit = models.CharField(max_length=100)
    delivery_hour = models.IntegerField()
    flow = models.ForeignKey(Flow, null=True, blank=True)
    message = models.TextField(null=True, blank=True)  # todo: this might need to also support dicts
    created_on = models.DateTimeField()

    rapidpro_collection = 'campaign_events'

    def __unicode__(self):
        return "%s - %s" % (self.uuid, self.organization)


def get_warehouse_attr_for_rapidpro_key(key):
    return 'rapidpro_id' if key == 'id' else key
