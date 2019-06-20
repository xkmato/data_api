from __future__ import unicode_literals
import csv
from datetime import datetime
import logging
from bson.errors import InvalidId
from bson.objectid import ObjectId
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from mongoengine import connect, Document, StringField, BooleanField, ReferenceField, DateTimeField, IntField, \
    EmbeddedDocument, ListField, EmbeddedDocumentField, DictField, DynamicDocument, FloatField, DynamicField, \
    MapField, ObjectIdField
from rest_framework.authtoken.models import Token
from temba_client.exceptions import TembaNoSuchObjectError, TembaException
from temba_client.v2 import TembaClient

from data_api.api.ingestion import RapidproAPIBaseModel, get_fetch_kwargs
from data_api.api.utils import create_folder_for_org

__author__ = 'kenneth'

if getattr(settings, 'MONGO_USERNAME', None):
    connect(db=settings.MONGO_DBNAME, username=settings.MONGO_USERNAME, password=settings.MONGO_PASSWORD)
else:
    connect(db=settings.MONGO_DBNAME)

logging.basicConfig(format=settings.LOG_FORMAT)
logger = logging.getLogger("models")


class Org(Document):
    api_token = StringField(required=True)
    server = StringField(required=True, default=settings.RAPIDPRO_DEFAULT_SITE)
    is_active = BooleanField(default=False)
    name = StringField(required=True)
    country = StringField()
    languages = ListField(StringField())
    primary_language = StringField()
    timezone = StringField(default="UTC")
    date_style = StringField()
    credits = DictField()
    anon = BooleanField()
    meta = {'collection': 'orgs'}

    @classmethod
    def create(cls, name, api_token, timezone):
        o = cls(name=name, api_token=api_token, timezone=timezone)
        o.save()
        return o

    def get_temba_client(self):
        return TembaClient(self.server, self.api_token)

    def __unicode__(self):
        return self.name

    def get_runs(self):
        return Run.objects.filter(org__id=self.id)

    def get_contacts(self):
        return Contact.objects.filter(org__id=self.id)

    def get_flows(self):
        return Flow.objects.filter(org__id=self.id)


class LastSaved(DynamicDocument):
    org = ReferenceField('Org')
    coll = StringField()
    last_saved = DateTimeField()
    last_started = DateTimeField()
    is_running = BooleanField(default=False)

    @classmethod
    def get_for_org_and_collection(cls, org, collection_class):
        return cls.objects.filter(**{'coll': collection_class.get_collection_name(), 'org': org}).first()

    @classmethod
    def create_for_org_and_collection(cls, org, collection_class):
        ls = cls()
        ls.org = org
        ls.coll = collection_class.get_collection_name()
        return ls


class BaseUtil(RapidproAPIBaseModel):

    @classmethod
    def get_collection_name(cls):
        return cls._meta['collection']

    @classmethod
    def object_count(cls, org):
        return cls.objects.filter(org_id=org.id).count()

    @classmethod
    def bulk_save(cls, chunk_to_save):
        cls.objects.insert(chunk_to_save)

    @classmethod
    def create_from_temba(cls, org, temba, do_save=True):
        obj = cls()
        for key, value in temba.__dict__.items():
            class_attr = getattr(cls, key, None)
            logger.debug('setting {} to {}'.format(key, value))
            if class_attr is None:
                continue
            if isinstance(class_attr, ListField):
                item_class = class_attr.field
                if isinstance(item_class, EmbeddedDocumentField):
                    item_class = item_class.document_type
                    setattr(obj, key, item_class.instantiate_from_temba_list(getattr(temba, key)))
                elif isinstance(item_class, ReferenceField):
                    # this is an opportunity to improve performance.
                    # rather than querying our local DB for the object and using a ReferenceField,
                    # we could instead just set an ID on the current document and not bother with
                    # doing explicit mongo references.
                    # this would avoid a huge number of DB lookups.
                    # An alternative option would be to just cache the result of this call
                    # so that multiple queries, e.g. to the same Contact, resolve quickly.
                    # Caching might introduce complex invalidation logic - e.g. if a model was imported
                    # midway through a full import.
                    uuids = [v.uuid for v in getattr(temba, key)]
                    setattr(obj, key, item_class.document_type.get_objects_from_uuids(org, uuids))
                else:
                    setattr(obj, key, value)
            elif isinstance(class_attr, MapField):
                item_class = class_attr.field
                assert isinstance(item_class, EmbeddedDocumentField)
                setattr(obj, key, {
                    k: item_class.document_type.instantiate_from_temba(v) for k, v in getattr(temba, key).items()
                })

            elif isinstance(class_attr, ReferenceField) and getattr(temba, key) is not None:
                item_class = class_attr.document_type
                # same note applies as above on the list version
                setattr(obj, key, item_class.get_or_fetch(org, getattr(temba, key).uuid))
            elif isinstance(class_attr, EmbeddedDocumentField):
                item_class = class_attr.document_type
                setattr(obj, key, item_class.instantiate_from_temba(getattr(temba, key)))
            else:
                if key == 'id':
                    key = 'tid'
                setattr(obj, key, value)

        obj.org_id = str(org['id'])
        obj.first_synced = datetime.utcnow()
        obj.last_synced = datetime.utcnow()
        if do_save:
            obj.save()
        return obj

    @classmethod
    def get_or_fetch(cls, org, uuid):
        if uuid is None:
            return None
        if hasattr(cls, 'uuid'):
            obj = cls.objects.filter(uuid=uuid).first()
        else:
            obj = cls.objects.filter(tid=uuid).first()
        if not obj:
            try:
                obj = cls.fetch(org, uuid)
            except (TembaNoSuchObjectError, TembaException, AttributeError):
                obj = None
        return obj

    @classmethod
    def fetch(cls, org, uuid):
        func = "get_%s" % cls.get_collection_name()
        fetch = getattr(org.get_temba_client(), func.rstrip('s'))
        return cls.create_from_temba(org, fetch(uuid))

    @classmethod
    def get_objects_from_uuids(cls, org, uuids):
        objs = []
        for uuid in uuids:
            obj = cls.get_or_fetch(org, uuid)
            if obj is None:
                continue
            else:
                objs.append(cls.get_or_fetch(org, uuid))
        return objs

    # def __unicode__(self):
    # if hasattr(self, 'name'):
    #         return '%s - %s' % (self.name, self.org)
    #     return "Base Util Object"

    @classmethod
    def get_for_org(cls, org):
        try:
            return cls.objects.filter(org_id=org)
        except InvalidId:
            return cls.objects.none()


class EmbeddedUtil(object):
    @classmethod
    def instantiate_from_temba(cls, temba):
        if temba is None:
            return None
        obj = cls()
        for k, v in temba.__dict__.items():
            setattr(obj, k, v)
        return obj

    @classmethod
    def instantiate_from_temba_list(cls, temba_list):
        obj_list = []
        for temba in temba_list:
            obj_list.append(cls.instantiate_from_temba(temba))
        return obj_list


class OrgDocument(Document, BaseUtil):
    org_id = ObjectIdField(required=True)
    first_synced = DateTimeField()
    last_synced = DateTimeField()

    meta = {'abstract': True}


class Group(OrgDocument):
    uuid = StringField()
    name = StringField()
    query = StringField()
    count = IntField()

    meta = {'collection': 'groups'}


class Device(EmbeddedDocument, EmbeddedUtil):
    power_status = StringField()
    power_source = StringField()
    power_level = IntField()
    name = StringField()
    network_type = StringField()


class Channel(OrgDocument):
    uuid = StringField()
    name = StringField()
    address = StringField()
    country = StringField()
    device = EmbeddedDocumentField(Device)
    last_seen = DateTimeField()
    created_on = DateTimeField()

    meta = {'collection': 'channels'}


class ChannelEvent(OrgDocument):
    tid = IntField()
    type = StringField()
    contact = ReferenceField('Contact')
    channel = ReferenceField('Channel')
    extra = DictField()
    occurred_on = DateTimeField()
    created_on = DateTimeField()

    meta = {'collection': 'channel_events'}


class Urn(EmbeddedDocument, EmbeddedUtil):
    type = StringField()
    identity = StringField()

    @classmethod
    def instantiate_from_temba(cls, temba):
        urn = cls()
        if temba and len(temba.split(':')) > 1:
            urn.type, urn.identity = tuple(temba.split(':'))
            return urn
        urn.identity = temba
        return urn

    def __unicode__(self):
        return u'{}:{}'.format(self.type, self.identity)


class Contact(OrgDocument):
    uuid = StringField()
    name = StringField()
    language = StringField()
    urns = ListField(EmbeddedDocumentField(Urn))
    groups = ListField(ReferenceField('Group'))
    fields = DictField()
    blocked = BooleanField()
    stopped = BooleanField()
    created_on = DateTimeField()
    modified_on = DateTimeField()

    meta = {'collection': 'contacts'}


class Field(OrgDocument):
    key = StringField()
    label = StringField()
    value_type = StringField()

    meta = {'collection': 'fields'}


class Broadcast(OrgDocument):
    tid = IntField()
    urns = ListField(EmbeddedDocumentField(Urn))
    contacts = ListField(ReferenceField('Contact'))
    groups = ListField(ReferenceField('Group'))
    text = DynamicField()
    created_on = DateTimeField()

    meta = {'collection': 'broadcasts'}

    def __unicode__(self):
        return "{} - {}".format(self.text, self.org_id)


class Campaign(OrgDocument):
    uuid = StringField()
    group = ReferenceField('Group')
    archived = BooleanField()
    created_on = DateTimeField()
    name = StringField()

    meta = {'collection': 'campaigns'}


class FieldRef(EmbeddedDocument, EmbeddedUtil):
    key = StringField()
    label = StringField()


class CampaignEvent(OrgDocument):
    uuid = StringField()
    campaign = ReferenceField(Campaign)
    relative_to = EmbeddedDocumentField(FieldRef)
    offset = IntField()
    unit = StringField()
    delivery_hour = IntField()
    flow = ReferenceField('Flow')
    message = DynamicField()
    created_on = DateTimeField()

    meta = {'collection': 'campaign_events'}

    def __unicode__(self):
        return "%s - %s" % (self.uuid, self.org)


class Ruleset(EmbeddedDocument, EmbeddedUtil):
    uuid = StringField()
    label = StringField()
    response_type = StringField()

    def __unicode__(self):
        return self.label


class Label(OrgDocument):
    uuid = StringField()
    name = StringField()
    count = IntField()

    meta = {'collection': 'labels'}


class Runs(EmbeddedDocument, EmbeddedUtil):
    active = IntField()
    completed = IntField()
    expired = IntField()
    interrupted = IntField()

class Flow(OrgDocument):
    uuid = StringField()
    name = StringField()
    archived = BooleanField()
    labels = ListField(ReferenceField('Label'))
    expires = IntField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    runs = EmbeddedDocumentField(Runs)

    meta = {'collection': 'flows'}

    def get_runs(self, queryset=None):
        if queryset:
            return queryset.filter(flow__id=self.id)
        return Run.objects.filter(flow__id=self.id)


class FlowStart(OrgDocument):
    uuid = StringField()
    flow = ReferenceField(Flow)
    groups = ListField(ReferenceField('Group'))
    contacts = ListField(ReferenceField('Contact'))
    restart_participants = BooleanField()
    status = StringField()
    extra = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()

    meta = {'collection': 'flow_starts'}


class Message(OrgDocument):
    tid = IntField()
    broadcast = IntField()
    contact = ReferenceField('Contact')
    urn = EmbeddedDocumentField(Urn)
    channel = ReferenceField('Channel')
    direction = StringField()
    type = StringField()
    status = StringField()
    visibility = StringField()
    text = StringField()
    labels = ListField(ReferenceField('Label'))
    created_on = DateTimeField()
    modified_on = DateTimeField()
    sent_on = DateTimeField()

    meta = {'collection': 'messages'}

    def __unicode__(self):
        return "%s - %s" % (self.text[:7], self.org_id)

    @staticmethod
    def _get_last_saved_id(folder):
        return 'messages:{}'.format(folder)

    @staticmethod
    def get_last_saved_for_folder(org, folder):
        return LastSaved.objects.filter(**{'coll': Message._get_last_saved_id(folder), 'org': org}).first()

    @staticmethod
    def create_last_saved_for_folder(org, folder):
        ls = LastSaved()
        ls.org = org
        ls.coll = Message._get_last_saved_id(folder)
        return ls

    @classmethod
    def sync_data_with_checkpoint(cls, org, checkpoint, return_objs=False):
        fetch_method = cls.get_fetch_method(org)
        fetch_kwargs = get_fetch_kwargs(fetch_method, checkpoint)
        folders = [
            'inbox', 'flows', 'archived', 'outbox', 'incoming', 'sent',
        ]
        objs = []
        initial_import = cls.objects.filter(org_id=org.id).count() == 0
        for folder in folders:
            logger.info('Syncing message folder {}'.format(folder))
            last_saved_for_folder = cls.get_last_saved_for_folder(org, folder)
            folder_kwargs = get_fetch_kwargs(fetch_method, last_saved_for_folder) or fetch_kwargs
            checkpoint = datetime.utcnow()
            temba_objs = fetch_method(folder=folder, **folder_kwargs)
            created_objs = cls.create_from_temba_list(org, temba_objs, return_objs, is_initial_import=initial_import)
            if return_objs:
                objs.extend(created_objs)
            if not last_saved_for_folder:
                last_saved_for_folder = cls.create_last_saved_for_folder(org, folder)
            last_saved_for_folder.last_saved = checkpoint
            last_saved_for_folder.save()
        return objs

class Value(EmbeddedDocument, EmbeddedUtil):
    value = DynamicField()
    category = StringField()
    node = StringField()
    time = DateTimeField()

    def __unicode__(self):
        return unicode(self.value)[:7]


class Step(EmbeddedDocument, EmbeddedUtil):
    node = StringField()
    time = DateTimeField()

    def __unicode__(self):
        return self.text[:7]


class Run(OrgDocument):
    tid = IntField()
    flow = ReferenceField('Flow')
    contact = ReferenceField('Contact')
    start = ReferenceField('FlowStart')
    responded = BooleanField()
    path = ListField(EmbeddedDocumentField(Step))
    values = MapField(EmbeddedDocumentField(Value))
    created_on = DateTimeField()
    modified_on = DateTimeField()
    exited_on = DateTimeField()
    exit_type = StringField()

    meta = {'collection': 'runs'}

    def __unicode__(self):
        return "For flow %s - %s" % (self.flow, self.org)

    @classmethod
    def get_for_flow(cls, flow_id):
        try:
            return cls.objects.filter(flow__id=ObjectId(flow_id))
        except InvalidId:
            return cls.objects.none()


class BoundaryRef(EmbeddedDocument, EmbeddedUtil):
    osm_id = StringField()
    name = StringField()


class Geometry(EmbeddedDocument, EmbeddedUtil):
    type = StringField()
    coordinates = ListField(ListField(ListField(ListField(FloatField()))))  # turtles all the way down

    def __unicode__(self):
        return self.coordinates


class Boundary(OrgDocument):
    created_on = DateTimeField()
    modified_on = DateTimeField()
    osm_id = StringField(required=True)
    name = StringField()
    level = IntField()
    parent = EmbeddedDocumentField(BoundaryRef)
    aliases = ListField(StringField())
    geometry = EmbeddedDocumentField(Geometry)

    meta = {'collection': 'boundaries'}


class Resthook(OrgDocument):
    resthook = StringField(required=True)
    created_on = DateTimeField()
    modified_on = DateTimeField()

    meta = {'collection': 'resthooks'}


class ResthookEvent(OrgDocument):
    resthook = StringField(required=True)
    data = DictField()
    created_on = DateTimeField()

    meta = {'collection': 'resthook_events'}


class ResthookSubscriber(OrgDocument):
    tid = IntField(required=True)
    resthook = StringField(required=True)
    target_url = StringField()
    created_on = DateTimeField()

    meta = {'collection': 'resthook_subscribers'}


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
