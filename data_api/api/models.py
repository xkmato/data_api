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
    MapField
from rest_framework.authtoken.models import Token
from temba_client.exceptions import TembaNoSuchObjectError, TembaException
from temba_client.v2 import TembaClient
from data_api.api.utils import create_folder_for_org

__author__ = 'kenneth'

if getattr(settings, 'MONGO_USERNAME', None):
    connect(db="rapidpro", username=settings.MONGO_USERNAME, password=settings.MONGO_PASSWORD)
else:
    connect(db='rapidpro')

logging.basicConfig(format=settings.LOG_FORMAT)
logger = logging.getLogger("models")


class CSVExport(models.Model):
    org_id = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    last_object = models.DateTimeField()
    object_model = models.CharField(max_length=100)

    @classmethod
    def update_for_object(cls, org_id, obj_id, obj_type):
        obj = cls.objects.filter(object_model=obj_type, org_id=org_id).first()
        if not obj:
            obj = cls.objects.create(object_model=obj_type, last_object=obj_id, org_id=org_id)
        else:
            obj.last_object = obj_id
            obj.save()
        return obj

    @classmethod
    def update_for_messages(cls, org_id, obj_id):
        return cls.update_for_object(org_id, obj_id, 'message')

    @classmethod
    def update_for_runs(cls, org_id, obj_id):
        return cls.update_for_object(org_id, obj_id, 'run')

    @classmethod
    def get_last_object(cls, org, obj_type):
        return cls.objects.filter(object_model=obj_type, org_id=org)

    @classmethod
    def get_last_message(cls, org):
        return cls.get_last_object(org, 'message')

    @classmethod
    def get_last_run(cls, org):
        return cls.get_last_object(org, 'run')


class Org(Document):
    api_token = StringField(required=True)
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
    def import_from_temba(cls, temba_client, api_key):
        org = temba_client.get_org()
        org_dict = org.serialize()
        org_dict['api_token'] = api_key
        local_org = Org(**org_dict)
        local_org.save()
        return local_org


    @classmethod
    def create(cls, name, api_token, timezone):
        o = cls(name=name, api_token=api_token, timezone=timezone)
        o.save()
        return o

    def get_temba_client(self):
        host = getattr(settings, 'SITE_API_HOST', None)
        agent = getattr(settings, 'SITE_API_USER_AGENT', None)

        if not host:
            host = '%s/api/v1' % settings.API_ENDPOINT  # UReport sites use this

        return TembaClient(host, self.api_token, user_agent=agent)

    def __unicode__(self):
        return self.name

    def get_runs(self):
        return Run.objects.filter(org__id=self.id)

    def get_contacts(self):
        return Contact.objects.filter(org__id=self.id)

    def get_flows(self):
        return Flow.objects.filter(org__id=self.id)


class LastSaved(DynamicDocument):
    coll = StringField()
    org = DictField()
    last_saved = DateTimeField()


class BaseUtil(object):
    @classmethod
    def create_from_temba(cls, org, temba):
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
                    setattr(obj, key, item_class.create_from_temba_list(getattr(temba, key)))
                elif isinstance(item_class, ReferenceField):
                    uuids = [v.uuid for v in getattr(temba, key)]
                    setattr(obj, key, item_class.document_type.get_objects_from_uuids(org, uuids))
                else:
                    setattr(obj, key, value)
            elif isinstance(class_attr, MapField):
                item_class = class_attr.field
                assert isinstance(item_class, EmbeddedDocumentField)
                setattr(obj, key, {
                    k: item_class.document_type.create_from_temba(v) for k, v in getattr(temba, key).items()
                })

            elif isinstance(class_attr, ReferenceField) and getattr(temba, key) is not None:
                item_class = class_attr.document_type
                setattr(obj, key, item_class.get_or_fetch(org, getattr(temba, key).uuid))
            elif isinstance(class_attr, EmbeddedDocumentField):
                item_class = class_attr.document_type
                setattr(obj, key, item_class.create_from_temba(getattr(temba, key)))
            else:
                if key == 'id':
                    key = 'tid'
                setattr(obj, key, value)

        obj.org_id = str(org['id'])
        obj.save()
        return obj

    @classmethod
    def get_or_fetch(cls, org, uuid):
        if uuid == None: return None
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
        func = "get_%s" % cls._meta['collection']
        fetch = getattr(org.get_temba_client(), func.rstrip('s'))
        return cls.create_from_temba(org, fetch(uuid))

    @classmethod
    def create_from_temba_list(cls, org, temba_list):
        obj_list = []
        q = None
        for temba in temba_list.all():
            if hasattr(temba, 'uuid'):
                q = {'uuid': temba.uuid}
            elif hasattr(temba, 'id'):
                q = {'tid': temba.id}
            if not q or not cls.objects.filter(**q).first():
                obj_list.append(cls.create_from_temba(org, temba))
        return obj_list

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

    @classmethod
    def fetch_objects(cls, org, pager=None):
        func = "get_%s" % cls._meta['collection']
        ls = LastSaved.objects.filter(**{'coll': cls._meta['collection'], 'org__id': org.id}).first()
        after = getattr(ls, 'last_saved', None)
        fetch_all = getattr(org.get_temba_client(), func)
        try:
            objs = cls.create_from_temba_list(org, fetch_all(after=after, pager=pager))
            if not ls:
                ls = LastSaved()
                ls.org = org
            ls.coll = cls._meta['collection']
            ls.last_saved = datetime.now(tz=org.timezone)
            ls.save()
        except TypeError:
            try:
                objs = cls.create_from_temba_list(org, fetch_all(pager=pager))
            except TypeError:
                objs = cls.create_from_temba_list(org, fetch_all())
        return objs

    # def __unicode__(self):
    # if hasattr(self, 'name'):
    #         return '%s - %s' % (self.name, self.org)
    #     return "Base Util Object"

    @classmethod
    def get_for_org(cls, org):
        try:
            return cls.objects.filter(org__id=ObjectId(org))
        except InvalidId:
            return cls.objects.none()


class EmbeddedUtil(object):
    @classmethod
    def create_from_temba(cls, temba):
        if temba is None:
            return None
        obj = cls()
        for k, v in temba.__dict__.items():
            setattr(obj, k, v)
        return obj

    @classmethod
    def create_from_temba_list(cls, temba_list):
        obj_list = []
        for temba in temba_list:
            obj_list.append(cls.create_from_temba(temba))
        return obj_list


class Group(Document, BaseUtil):
    org_id = StringField(required=True)
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


class Channel(Document, BaseUtil):
    org_id = StringField(required=True)
    uuid = StringField()
    name = StringField()
    address = StringField()
    country = StringField()
    device = EmbeddedDocumentField(Device)
    last_seen = DateTimeField()
    created_on = DateTimeField()

    meta = {'collection': 'channels'}


class ChannelEvent(Document, BaseUtil):
    tid = IntField()
    type = StringField()
    contact = ReferenceField('Contact')
    channel = ReferenceField('Channel')
    time = DateTimeField()
    duration = IntField()
    created_on = DateTimeField()

    meta = {'collection': 'channel_events'}


class Urn(EmbeddedDocument, EmbeddedUtil):
    type = StringField()
    identity = StringField()

    @classmethod
    def create_from_temba(cls, temba):
        urn = cls()
        if temba and len(temba.split(':')) > 1:
            urn.type, urn.identity = tuple(temba.split(':'))
            return urn
        urn.identity = temba
        return urn

    def __unicode__(self):
        return u'{}:{}'.format(self.type, self.identity)


class Contact(Document, BaseUtil):
    org_id = StringField(required=True)
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


class Field(Document, BaseUtil):
    org_id = StringField(required=True)
    key = StringField()
    label = StringField()
    value_type = StringField()

    meta = {'collection': 'fields'}


class Broadcast(Document, BaseUtil):
    org_id = StringField(required=True)
    tid = IntField()
    urns = ListField(EmbeddedDocumentField(Urn))
    contacts = ListField(ReferenceField('Contact'))
    groups = ListField(ReferenceField('Group'))
    text = DynamicField()
    created_on = DateTimeField()

    meta = {'collection': 'broadcasts'}

    def __unicode__(self):
        return "%s - %s" % (self.text[:7], self.org)


class Campaign(Document, BaseUtil):
    org_id = StringField(required=True)
    uuid = StringField()
    group = ReferenceField('Group')
    created_on = DateTimeField()
    name = StringField()

    meta = {'collection': 'campaigns'}


class FieldRef(EmbeddedDocument, EmbeddedUtil):
    key = StringField()
    label = StringField()


class CampaignEvent(Document, BaseUtil):
    uuid = StringField()
    campaign = ReferenceField(Campaign)
    relative_to = EmbeddedDocumentField(FieldRef)
    offset = IntField()
    unit = StringField()
    delivery_hour = IntField()
    flow = ReferenceField('Flow')
    message = StringField()
    created_on = DateTimeField()

    meta = {'collection': 'campaign_events'}

class Ruleset(EmbeddedDocument, EmbeddedUtil):
    uuid = StringField()
    label = StringField()
    response_type = StringField()

    def __unicode__(self):
        return self.label


class Label(Document, BaseUtil):
    org_id = StringField(required=True)
    uuid = StringField()
    name = StringField()
    count = IntField()

    meta = {'collection': 'labels'}


class Runs(EmbeddedDocument, EmbeddedUtil):
    active = IntField()
    completed = IntField()
    expired = IntField()
    interrupted = IntField()

    def __unicode__(self):
        return self.label


class Flow(Document, BaseUtil):
    org_id = StringField(required=True)
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


class FlowStart(Document, BaseUtil):
    org_id = StringField(required=True)
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


class Event(Document, BaseUtil):
    # todo: rename to CampaignEvent?
    org_id = StringField(required=True)
    created_on = DateTimeField()
    modified_on = DateTimeField()
    uuid = StringField()
    campaign = DictField()
    relative_to = StringField()
    offset = IntField()
    unit = StringField()
    delivery_hour = IntField()
    message = StringField()
    flow = DictField()

    meta = {'collection': 'campaign_events'}

    def __unicode__(self):
        return "%s - %s" % (self.uuid, self.org)


class Message(Document):
    # todo: add back inheritance from BaseUtil once figure out how to get all messages
    org_id = StringField(required=True)
    created_on = DateTimeField()
    modified_on = DateTimeField()
    tid = IntField()
    broadcast = DictField()
    contact = DictField()
    urn = EmbeddedDocumentField(Urn)
    status = StringField()
    type = StringField()
    labels = ListField(StringField())
    direction = StringField()
    archived = StringField()
    text = StringField()
    delivered_on = DateTimeField()
    sent_on = DateTimeField()

    meta = {'collection': 'messages'}

    def __unicode__(self):
        return "%s - %s" % (self.text[:7], self.org)

    @classmethod
    def generate_csv(cls, from_date=None, org_id=None, contact_fields=None):
        if not from_date:
            from_date = datetime(2016, 1, 1)
        if not org_id:
            org_id = settings.DEFAULT_ORG
        create_folder_for_org(org_id)
        if not contact_fields:
            contact_fields = settings.DEFAULT_CONTACT_FIELDS

        message_attributes = settings.DEFAULT_MESSAGE_ATTRIBUTES
        file_number = 0
        record_number = 0
        q = cls.get_for_org(org_id).filter(created_on__gt=from_date)
        while q[record_number: record_number + settings.MAX_RECORDS_PER_EXPORT].first():
            with open('%s/%s/messages/export_%s_%d.csv' % (settings.CSV_DUMPS_FOLDER, org_id, str(datetime.now()),
                                                           file_number), 'w') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=message_attributes + ['contact_%s' % a
                                                                                   for a in contact_fields])
                writer.writeheader()
                for message in q[record_number: record_number + settings.MAX_RECORDS_PER_EXPORT]:
                    try:
                        contact = Contact.objects.filter(id=ObjectId(message.contact.get('id'))).first()
                        if contact:
                            try:
                                fields = eval(contact.fields)
                            except NameError:
                                fields = {}

                        m_dict = {}
                        for attrib in message_attributes:
                            m_dict[attrib] = unicode(getattr(message, attrib)).encode('utf-8')
                        if contact:
                            m_dict['contact_uuid'] = contact.uuid
                            contact_fields.remove('uuid')
                            for _attrib in contact_fields:
                                m_dict['contact_%s' % _attrib] = unicode(fields.get(_attrib)).encode('utf-8')
                        writer.writerow(m_dict)
                        record_number += 1
                        if record_number >= record_number+settings.MAX_RECORDS_PER_EXPORT:
                            break
                    except UnicodeEncodeError as e:
                        logger.error(e)
                        #Todo Figure out what todo here
                    except Exception as e:
                        logger.error(e)
                CSVExport.update_for_messages(org_id, message.created_on)
            file_number += 1


class Value(EmbeddedDocument, EmbeddedUtil):
    value = StringField()
    category = StringField()
    node = StringField()
    time = DateTimeField()

    def __unicode__(self):
        return self.value[:7]


class Step(EmbeddedDocument, EmbeddedUtil):
    node = StringField()
    time = DateTimeField()

    def __unicode__(self):
        return self.text[:7]


class Run(Document, BaseUtil):
    org_id = StringField(required=True)
    tid = IntField()
    flow = ReferenceField('Flow')
    contact = ReferenceField('Contact')
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

    @classmethod
    def generate_csv(cls, from_date=None, org_id=None, contact_fields=None):
        if not org_id:
            org_id = settings.DEFAULT_ORG
        create_folder_for_org(org_id)
        if not from_date:
            from_date = datetime(2016, 1, 1)
        if not contact_fields:
            contact_fields = settings.DEFAULT_CONTACT_FIELDS

        step_attributes = ['node', 'text', 'value', 'type', 'arrived_on', 'left_on']
        ruleset_attributes = ['node', 'category', 'text', 'rule_value', 'label', 'value', 'time']
        run_attributes = ['created_on', 'kind', 'flow_uuid', 'flow_name']
        file_number = 0
        record_number = 0
        q = cls.get_for_org(org_id).filter(created_on__gt=from_date, values__ne=[]).order_by('created_on')
        while q[record_number: record_number + settings.MAX_RECORDS_PER_EXPORT].first():
            try:
                with open('%s/%s/runs/export_%s_%d.csv' % (settings.CSV_DUMPS_FOLDER, org_id, str(datetime.now()),
                                                               file_number), 'w') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=run_attributes + ['step_%s' % sa for sa in step_attributes]
                                                                    + ['ruleset_%s' % ra for ra in ruleset_attributes] +
                                                                    ['contact_%s' % a for a in contact_fields])
                    writer.writeheader()
                    for run in q[record_number: record_number + settings.MAX_RECORDS_PER_EXPORT]:
                        try:
                            flow = Flow.objects.filter(id=ObjectId(run.flow.get('id'))).first()
                            contact = Contact.objects.filter(id=ObjectId(run.contact.get('id'))).first()
                            if contact:
                                try:
                                    fields = eval(contact.fields)
                                except NameError:
                                    fields = {}

                            m_dict = {'created_on': unicode(run.created_on), 'flow_uuid': flow.uuid if flow else None,
                                      'flow_name': flow.name if flow else None}
                            if contact:
                                m_dict['contact_uuid'] = contact.uuid
                                contact_fields.remove('uuid')
                                for _attrib in contact_fields:
                                    m_dict['contact_%s' % _attrib] = unicode(fields.get(_attrib)).encode('utf-8')
                            r_dict, s_dict = {}, {}
                            try:
                                for ruleset in run.values:
                                    m_dict['kind'] = 'value'
                                    for ra in ruleset_attributes:
                                        r_dict['ruleset_%s' % ra] = unicode(getattr(ruleset, ra, None)).encode('utf-8')
                                    x = m_dict.copy()
                                    x.update(r_dict)
                                    writer.writerow(x)
                            except Exception as e:
                                logger.error(e)
                            record_number += 1
                            if record_number >= record_number+settings.MAX_RECORDS_PER_EXPORT:
                                break
                        except UnicodeEncodeError as e:
                            logger.error(e)
                            #Todo Figure out what todo here
                        except Exception as e:
                            logger.error(e)
                    CSVExport.update_for_runs(org_id, run.created_on)
                file_number += 1
            except Exception as e:
                pass


class CategoryStats(EmbeddedDocument, EmbeddedUtil):
    count = IntField()
    label = StringField()

    def __unicode__(self):
        return self.label


class Result(Document):
    # todo: add back inheritance from BaseUtil once we figure out where this model went (or delete it)
    org_id = StringField(required=True)
    created_on = DateTimeField()
    modified_on = DateTimeField()
    boundary = StringField()
    set = IntField()
    unset = IntField()
    open_ended = StringField()
    label = StringField()
    categories = ListField(EmbeddedDocumentField(CategoryStats))

    meta = {'collection': 'results'}

    def __unicode__(self):
        return "%s - %s" % (self.label, self.org)


class BoundaryRef(EmbeddedDocument, EmbeddedUtil):
    osm_id = StringField()
    name = StringField()


class Geometry(EmbeddedDocument, EmbeddedUtil):
    type = StringField()
    coordinates = ListField(ListField(ListField(ListField(FloatField()))))  # turtles all the way down

    def __unicode__(self):
        return self.coordinates


class Boundary(Document, BaseUtil):
    org_id = StringField(required=True)
    created_on = DateTimeField()
    modified_on = DateTimeField()
    osm_id = StringField(required=True)
    name = StringField()
    level = IntField()
    parent = EmbeddedDocumentField(BoundaryRef)
    aliases = ListField(StringField())
    geometry = EmbeddedDocumentField(Geometry)

    meta = {'collection': 'boundaries'}


class Resthook(Document, BaseUtil):
    org_id = StringField(required=True)
    resthook = StringField(required=True)
    created_on = DateTimeField()
    modified_on = DateTimeField()

    meta = {'collection': 'resthooks'}


class ResthookEvent(Document, BaseUtil):
    org_id = StringField(required=True)
    resthook = StringField(required=True)
    data = DictField()
    created_on = DateTimeField()

    meta = {'collection': 'resthook_events'}


class ResthookSubscriber(Document, BaseUtil):
    org_id = StringField(required=True)
    tid = IntField(required=True)
    resthook = StringField(required=True)
    target_url = StringField()
    created_on = DateTimeField()

    meta = {'collection': 'resthook_subscribers'}


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
