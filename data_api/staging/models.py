from __future__ import unicode_literals
from collections import namedtuple

from datetime import datetime

import os
import pytz
from django.conf import settings
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from temba_client.v2 import TembaClient, Message as TembaMessage

from data_api.api.exceptions import ImportRunningException
from data_api.api.ingestion import RapidproAPIBaseModel, get_fetch_kwargs, SqlIngestionCheckpoint, ensure_timezone, \
    download_archive_to_temporary_file, iter_archive
from data_api.api.models import logger

"""
RapidPro Staging SQL models live here. The word "staging" comes from the data warehouse 
notion of staging where the raw data from an external system is staged as-is in the warehouse.
Thus, these models represent the *raw* rapidpro data.

It is anticipated that there might one day be a "rapidpro_warehouse" app that aggregates/denormalizes
the staging data in a way to make data warehouse operations more efficient. 

Eventually this will replace the mongo models in api.models, but for the transition period
the intention is to have two models files, one for mongo and one for SQL.
"""

ModelToSave = namedtuple('ModelToSave', 'object foreign_key_field')


class MappedManyToManyField(models.ManyToManyField):
    """
    This is a ManyToManyField used to import rapidpro mapped related objects.
    It assumes the related object has a "key" field and sticks the key from
    the rapidpro map into that place.
    """
    pass


class Organization(models.Model):
    api_token = models.CharField(max_length=40)
    server = models.CharField(max_length=100, default=settings.RAPIDPRO_DEFAULT_SITE)
    is_active = models.BooleanField(default=False)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100, null=True, blank=True)
    primary_language = models.CharField(max_length=100, null=True, blank=True)
    languages = ArrayField(
        models.CharField(max_length=100)
    )
    credits = JSONField(default=dict)
    timezone = models.CharField(max_length=100, null=True, blank=True)
    date_style = models.CharField(max_length=100, null=True, blank=True)
    anon = models.BooleanField(default=False)

    def get_temba_client(self):
        return TembaClient(self.server, self.api_token)

    def __unicode__(self):
        return self.name


class SyncCheckpoint(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    collection_name = models.CharField(max_length=100)
    subcollection_name = models.CharField(max_length=100, null=True, blank=True)
    last_started = models.DateTimeField()
    last_saved = models.DateTimeField(null=True, blank=True)
    is_running = models.BooleanField(default=False)

    class Meta:
        unique_together = ('organization', 'collection_name', 'subcollection_name')

    def __unicode__(self):
        return '{}: {} {}'.format(self.organization, self.collection_name, self.subcollection_name or '').strip()


class RapidproCreateableModelMixin(object):
    """
    This mixin is for anything that can be created from a rapidpro temba api object,
    including base models and embedded/foreign-key models.
    """

    @classmethod
    def get_or_create_from_temba(cls, org, temba_value):
        try:
            return cls.objects.get(uuid=temba_value.uuid)
        except cls.DoesNotExist:
            return cls.create_from_temba(org, temba_value, do_save=True)

    @classmethod
    def create_from_temba(cls, org, temba, do_save=True):
        obj = cls()
        # will map field names to lists of fields to add, since all related models and the primary
        # need to be saved before we can save the relationship information
        related_models = {}
        post_save_related_models = []  # objects that we need to save after the primary object is saved
        for key, temba_value in temba.__dict__.items():
            warehouse_attr = get_warehouse_attr_for_rapidpro_key(key)
            try:
                field = cls._meta.get_field(warehouse_attr)
            except FieldDoesNotExist:
                continue

            if temba_value is None:
                continue
            elif isinstance(field, models.OneToOneField):
                # we have to save related models in django
                setattr(obj, warehouse_attr, field.related_model.create_from_temba(org, temba_value, do_save=True))
            elif isinstance(field, models.ForeignKey):
                # this is an opportunity to improve performance.
                # rather than querying our local DB for the object and using a ForeignKey,
                # we could instead just set an ID on the current document and not bother with
                # doing explicit foreign key references.
                # this would avoid a huge number of DB lookups.
                # An alternative option would be to just cache the result of this call
                # so that multiple queries, e.g. to the same Contact, resolve quickly.
                # Caching might introduce complex invalidation logic - e.g. if a model was imported
                # midway through a full import.
                setattr(obj, warehouse_attr, field.related_model.get_or_create_from_temba(org, temba_value))
            elif isinstance(field, MappedManyToManyField):
                assert isinstance(temba_value, dict), 'expected dict but was {} ({})'.format(type(temba_value),
                                                                                             temba_value)
                warehouse_models = []
                for key, nested_object in temba_value.iteritems():
                    nested_object.__dict__['key'] = key
                    warehouse_object = field.related_model.create_from_temba(org, nested_object, do_save=True)
                    warehouse_models.append(warehouse_object)
                related_models[warehouse_attr] = warehouse_models
            elif isinstance(field, models.ManyToManyField):
                assert isinstance(temba_value, list), 'expected list but was {} ({})'.format(type(temba_value),
                                                                                             temba_value)
                warehouse_models = []
                for nested_object in temba_value:
                    warehouse_object = field.related_model.get_or_create_from_temba(org, nested_object)
                    warehouse_models.append(warehouse_object)
                related_models[warehouse_attr] = warehouse_models
            elif isinstance(field, models.ManyToOneRel):
                assert isinstance(temba_value, list), 'expected list but was {} ({})'.format(type(temba_value),
                                                                                             temba_value)
                for nested_object in temba_value:
                    # instantiate, but don't save, a new instance of the related model
                    warehouse_object = field.related_model.create_from_temba(org, nested_object, do_save=False)
                    post_save_related_models.append(ModelToSave(object=warehouse_object,
                                                                foreign_key_field=field.remote_field.name))
            else:
                setattr(obj, warehouse_attr, temba_value)

        obj.organization = org
        if do_save or related_models or post_save_related_models:
            obj.save()
            for attr, related_objs in related_models.iteritems():
                for related_obj in related_objs:
                    getattr(obj, attr).add(related_obj)
            for model_to_save in post_save_related_models:
                # set the foreign key to the current object (this has to happen after the original model is saved)
                setattr(model_to_save.object, model_to_save.foreign_key_field, obj)
                model_to_save.object.save()
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
    name = models.TextField()
    query = models.TextField(null=True, blank=True)
    count = models.IntegerField()

    rapidpro_collection = 'groups'

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.organization)


class Contact(OrganizationModel):
    uuid = models.UUIDField()
    name = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=100, null=True, blank=True)
    urns = ArrayField(
        models.CharField(max_length=100),
        default=list
    )
    groups = models.ManyToManyField(Group)
    fields = JSONField(default=dict)
    blocked = models.NullBooleanField()
    stopped = models.NullBooleanField()
    created_on = models.DateTimeField(null=True, blank=True)
    modified_on = models.DateTimeField(null=True, blank=True)

    rapidpro_collection = 'contacts'

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.organization)


class Field(OrganizationModel):
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    value_type = models.CharField(max_length=100)

    rapidpro_collection = 'fields'

    def __unicode__(self):
        return '{} ({})'.format(self.label, self.organization)


class Device(RapidproBaseModel):
    power_status = models.CharField(max_length=100)
    power_source = models.CharField(max_length=100)
    power_level = models.IntegerField()
    name = models.CharField(max_length=100)
    network_type = models.CharField(max_length=100)

    def __unicode__(self):
        return '{}'.format(self.name)


class Channel(OrganizationModel):
    uuid = models.UUIDField()
    name = models.TextField(null=True, blank=True)
    address = models.TextField()
    country = models.CharField(max_length=100)
    device = models.OneToOneField(Device, null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_on = models.DateTimeField(null=True, blank=True)

    rapidpro_collection = 'channels'

    def __unicode__(self):
        return '{}'.format(self.name)


class ChannelEvent(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    type = models.CharField(max_length=100, null=True, blank=True)
    contact = models.ForeignKey(Contact)
    channel = models.ForeignKey(Channel)
    extra = JSONField(default=dict)
    occurred_on = models.DateTimeField()
    created_on = models.DateTimeField()

    rapidpro_collection = 'channel_events'


class Broadcast(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    urns = ArrayField(
        models.CharField(max_length=100),
        default=list
    )
    contacts = models.ManyToManyField(Contact)
    groups = models.ManyToManyField(Group)
    text = models.TextField()  # todo: this might need to also support dicts
    created_on = models.DateTimeField()

    rapidpro_collection = 'broadcasts'

    def __unicode__(self):
        return "{}".format(self.text)


class Campaign(OrganizationModel):
    uuid = models.UUIDField()
    group = models.ForeignKey(Group, null=True, blank=True)
    archived = models.BooleanField(default=False)
    created_on = models.DateTimeField()
    name = models.CharField(max_length=100)

    rapidpro_collection = 'campaigns'

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.organization)


class Label(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100)
    count = models.IntegerField(null=True, blank=True)

    rapidpro_collection = 'labels'

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.organization)


class Runs(RapidproBaseModel):
    active = models.IntegerField(default=0)
    completed = models.IntegerField(default=0)
    expired = models.IntegerField(default=0)
    interrupted = models.IntegerField(default=0)


class Flow(OrganizationModel):
    uuid = models.UUIDField()
    name = models.CharField(max_length=100)
    archived = models.BooleanField(default=False)
    labels = models.ManyToManyField(Label)
    expires = models.IntegerField(null=True, blank=True)
    created_on = models.DateTimeField(null=True, blank=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    runs = models.OneToOneField(Runs, null=True, blank=True)

    rapidpro_collection = 'flows'

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.organization)


class FlowStart(OrganizationModel):
    uuid = models.UUIDField()
    flow = models.ForeignKey(Flow, null=True, blank=True)
    groups = models.ManyToManyField(Group)
    contacts = models.ManyToManyField(Contact)
    restart_participants = models.NullBooleanField()
    status = models.CharField(max_length=100)
    extra = JSONField(default=dict)
    created_on = models.DateTimeField(null=True, blank=True)
    modified_on = models.DateTimeField(null=True, blank=True)

    rapidpro_collection = 'flow_starts'


class CampaignEvent(OrganizationModel):
    uuid = models.UUIDField()
    campaign = models.ForeignKey(Campaign)
    # relative_to = EmbeddedDocumentField(FieldRef)
    offset = models.IntegerField()
    unit = models.CharField(max_length=100)
    delivery_hour = models.IntegerField()
    flow = models.ForeignKey(Flow, null=True, blank=True)
    message = models.TextField(null=True, blank=True)  # todo: this might need to also support dicts
    created_on = models.DateTimeField(null=True, blank=True)

    rapidpro_collection = 'campaign_events'

    def __unicode__(self):
        return "%s - %s" % (self.uuid, self.organization)


class Message(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    broadcast = models.PositiveIntegerField(null=True, blank=True)
    contact = models.ForeignKey(Contact)
    urn = models.CharField(max_length=100)
    channel = models.ForeignKey(Channel, null=True, blank=True)
    direction = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    visibility = models.CharField(max_length=100)
    text = models.TextField()
    labels = models.ManyToManyField(Label)
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField(null=True, blank=True)
    sent_on = models.DateTimeField(null=True, blank=True)

    rapidpro_collection = 'messages'

    def __unicode__(self):
        return "%s - %s" % (self.text[:7], self.organization)

    @classmethod
    def get_checkpoint_for_folder(cls, org, folder):
        return SqlIngestionCheckpoint(org, cls, datetime.now(tz=pytz.utc), folder)

    @classmethod
    def sync_data_with_checkpoint(cls, org, checkpoint, return_objs=False):
        initial_import = not cls.objects.filter(organization=org).exists()
        if settings.RAPIDPRO_USE_ARCHIVES:
            return cls._sync_from_archives(org, checkpoint, return_objs, initial_import)
        else:
            return cls._sync_from_apis(org, checkpoint, return_objs, initial_import)

    @classmethod
    def _sync_from_archives(cls, org, checkpoint, return_objs, initial_import):
        temba_class = TembaMessage
        archive_fetch_kwargs = {
            'archive_type': 'message',
            'period': 'monthly',
        }
        if checkpoint and checkpoint.exists() and checkpoint.get_last_checkpoint_time():
            archive_fetch_kwargs['after'] = ensure_timezone(checkpoint.get_last_checkpoint_time())

        def _iter_temba_objects():
            archives = org.get_temba_client().get_archives(**archive_fetch_kwargs)
            for archive in archives.all(retry_on_rate_exceed=True):
                logger.info('downloading archives for {} ({})'.format(archive.archive_type, archive.start_date))
                temp_file_name = download_archive_to_temporary_file(archive.download_url)
                for temba_json in iter_archive(temp_file_name):
                    try:
                        yield temba_class.deserialize(temba_json)
                    except:
                        import json
                        print(json.dumps(temba_json, indent=2))
                        raise
                # cleanup
                os.remove(temp_file_name)

        cls.create_from_temba_list(org, _iter_temba_objects(), return_objs, initial_import)


    @classmethod
    def _sync_from_apis(cls, org, checkpoint, return_objs, initial_import):
        fetch_method = cls.get_fetch_method(org)
        fetch_kwargs = get_fetch_kwargs(fetch_method, checkpoint)
        folders = [
            'inbox', 'flows', 'archived', 'outbox', 'incoming', 'sent',
        ]
        objs = []
        for folder in folders:
            logger.info('Syncing message folder {}'.format(folder))
            checkpoint = cls.get_checkpoint_for_folder(org, folder)
            if not checkpoint.exists():
                checkpoint.create_and_start()
            elif checkpoint.is_running():
                raise ImportRunningException('Import for model {} in org {} still pending!'.format(
                    cls.__name__, org.name,
                ))
            folder_kwargs = get_fetch_kwargs(fetch_method, checkpoint) or fetch_kwargs
            temba_objs = fetch_method(folder=folder, **folder_kwargs)
            temba_obj_generator = temba_objs.all(retry_on_rate_exceed=True)
            created_objs = cls.create_from_temba_list(org, temba_obj_generator, return_objs,
                                                      is_initial_import=initial_import)
            if return_objs:
                objs.extend(created_objs)
            checkpoint.set_finished()

        return objs


class Value(RapidproBaseModel):
    key = models.CharField(max_length=100)
    value = models.TextField()  # todo: might need to be json
    category = models.CharField(max_length=100)
    node = models.CharField(max_length=100)
    time = models.DateTimeField()

    def __unicode__(self):
        return unicode(self.value)[:7]


class Run(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    flow = models.ForeignKey(Flow)
    contact = models.ForeignKey(Contact)
    start = models.ForeignKey(FlowStart, null=True, blank=True)
    responded = models.BooleanField()
    # todo: I think this should actually be a MappedReverseForeignKey (not a thing that exists yet)
    values = MappedManyToManyField(Value)
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField()
    exited_on = models.DateTimeField(null=True, blank=True)
    exit_type = models.CharField(max_length=100)

    rapidpro_collection = 'runs'


class Step(RapidproBaseModel):
    run = models.ForeignKey(Run, related_name='path')
    node = models.CharField(max_length=100)
    time = models.DateTimeField()

    def __unicode__(self):
        return self.text[:7]


class BoundaryRef(RapidproBaseModel):
    osm_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)


class Geometry(RapidproBaseModel):
    type = models.CharField(max_length=100)
    coordinates = ArrayField(
        ArrayField(
            ArrayField(
                ArrayField(models.FloatField())
            )
        ),
        default=list
    )

    def __unicode__(self):
        return self.type


class Boundary(OrganizationModel):
    created_on = models.DateTimeField(null=True, blank=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    osm_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    level = models.IntegerField()
    parent = models.OneToOneField(BoundaryRef, null=True, blank=True)
    # aliases = ListField(StringField())
    geometry = models.OneToOneField(Geometry, null=True)

    rapidpro_collection = 'boundaries'

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.organization)


class Resthook(OrganizationModel):
    resthook = models.CharField(max_length=100)
    created_on = models.DateTimeField()
    modified_on = models.DateTimeField()

    rapidpro_collection = 'resthooks'


class ResthookEvent(OrganizationModel):
    resthook = models.CharField(max_length=100)
    data = JSONField(default=dict)
    created_on = models.DateTimeField()

    rapidpro_collection = 'resthook_events'


class ResthookSubscriber(OrganizationModel):
    rapidpro_id = models.PositiveIntegerField()
    resthook = models.CharField(max_length=100)
    target_url = models.CharField(max_length=100)
    created_on = models.DateTimeField()

    rapidpro_collection = 'resthook_subscribers'


def get_warehouse_attr_for_rapidpro_key(key):
    return 'rapidpro_id' if key == 'id' else key
