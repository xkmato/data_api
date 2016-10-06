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
    EmbeddedDocument, ListField, EmbeddedDocumentField, DictField, DynamicDocument
from rest_framework.authtoken.models import Token
from temba import TembaClient
from temba.base import TembaNoSuchObjectError, TembaException
from data_api.api.utils import create_folder_for_org

__author__ = 'kenneth'

connect(db="rapidpro")

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
    name = StringField(required=True)
    language = StringField()
    timezone = StringField(default="UTC")
    api_token = StringField(required=True)
    is_active = BooleanField(default=False)
    meta = {'collection': 'orgs'}

    @classmethod
    def create(cls, *args):
        name, api_token, timezone = tuple(args)
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
            if class_attr is None:
                continue
            if isinstance(class_attr, ListField):
                item_class = class_attr.field
                if isinstance(item_class, EmbeddedDocumentField):
                    item_class = item_class.document_type_obj
                    setattr(obj, key, item_class.create_from_temba_list(getattr(temba, key)))
                elif isinstance(item_class, ReferenceField):
                    item_class = item_class.document_type_obj
                    setattr(obj, key, item_class.get_objects_from_uuids(org, getattr(temba, key)))
                else:
                    setattr(obj, key, value)
            elif isinstance(class_attr, ReferenceField):
                item_class = class_attr.document_type_obj
                setattr(obj, key, item_class.get_or_fetch(org, getattr(temba, key)))
            elif isinstance(class_attr, EmbeddedDocumentField):
                item_class = class_attr.document_type_obj
                setattr(obj, key, item_class.create_from_temba(getattr(temba, key)))
            else:
                if key == 'id':
                    key = 'tid'
                setattr(obj, key, value)

        obj.org = org
        obj.save()
        return obj

    @classmethod
    def get_or_fetch(cls, org, uuid):
        if uuid == None: return None
        if hasattr(cls, 'uuid'):
            obj = cls.objects.filter(uuid=uuid).first()
            if cls == Label:
                obj = cls.objects.filter(name=uuid).first()
        else:
            obj = cls.objects.filter(tid=uuid).first()
        if not obj:
            try:
                obj = cls.fetch(org, uuid)
            except (TembaNoSuchObjectError, TembaException):
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
        for temba in temba_list:
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
            try:
                objs.append(cls.get_or_fetch(org, uuid))
            except TembaNoSuchObjectError:
                continue
        return objs

    @classmethod
    def fetch_objects(cls, org, pager=None):
        func = "get_%s" % cls._meta['collection']
        ls = LastSaved.objects.filter(**{'coll': cls._meta['collection'], 'org.id': org.id}).first()
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
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    size = IntField()

    meta = {'collection': 'groups'}


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
        return self.identity


class Contact(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    urns = ListField(EmbeddedDocumentField(Urn))
    groups = ListField(DictField())
    language = StringField()
    fields = DictField()

    meta = {'collection': 'contacts'}


class Broadcast(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    tid = IntField()
    urns = ListField(EmbeddedDocumentField(Urn))
    contacts = ListField(DictField())
    groups = ListField(DictField())
    text = StringField()
    status = StringField()

    meta = {'collection': 'broadcasts'}

    def __unicode__(self):
        return "%s - %s" % (self.text[:7], self.org)


class Campaign(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    group = DictField()

    meta = {'collection': 'campaigns'}


class Ruleset(EmbeddedDocument, EmbeddedUtil):
    uuid = StringField()
    label = StringField()
    response_type = StringField()

    def __unicode__(self):
        return self.label


class Label(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    count = IntField()

    meta = {'collection': 'labels'}


class Flow(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    archived = BooleanField()
    labels = ListField(StringField())
    participants = IntField()
    runs = IntField()
    completed_runs = IntField()
    rulesets = ListField(EmbeddedDocumentField(Ruleset))

    meta = {'collection': 'flows'}

    def get_runs(self, queryset=None):
        if queryset:
            return queryset.filter(flow__id=self.id)
        return Run.objects.filter(flow__id=self.id)


class Event(Document, BaseUtil):
    org = DictField()
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

    meta = {'collection': 'events'}

    def __unicode__(self):
        return "%s - %s" % (self.uuid, self.org)


class Message(Document, BaseUtil):
    org = DictField()
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


class RunValueSet(EmbeddedDocument, EmbeddedUtil):
    node = StringField()
    category = DictField()
    text = StringField()
    rule_value = StringField()
    label = StringField()
    value = StringField()
    time = DateTimeField()

    def __unicode__(self):
        return self.text[:7]


class FlowStep(EmbeddedDocument, EmbeddedUtil):
    node = StringField()
    text = StringField()
    value = StringField()
    type = StringField()
    arrived_on = DateTimeField()
    left_on = DateTimeField()

    def __unicode__(self):
        return self.text[:7]


class Run(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    tid = IntField()
    flow = DictField()
    contact = DictField()
    steps = ListField(EmbeddedDocumentField(FlowStep))
    values = ListField(EmbeddedDocumentField(RunValueSet))
    completed = StringField()

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
        q = cls.get_for_org(org_id).filter(created_on__gt=from_date).order_by('created_on')
        while q[record_number: record_number + settings.MAX_RECORDS_PER_EXPORT].first():
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
                                record_number += 1
                        except Exception as e:
                            logger.error(e)
                        # try:
                        #     for step in run.steps:
                        #         m_dict['kind'] = 'step'
                        #         for sa in step_attributes:
                        #             s_dict['step_%s' % sa] = unicode(getattr(step, sa, None)).encode('utf-8')
                        #         x = m_dict.copy()
                        #         x.update(s_dict)
                        #         writer.writerow(x)
                        #         record_number += 1
                        # except Exception as e:
                        #     logger.error(e)
                        if record_number >= record_number+settings.MAX_RECORDS_PER_EXPORT:
                            break
                    except UnicodeEncodeError as e:
                        logger.error(e)
                        #Todo Figure out what todo here
                    except Exception as e:
                        logger.error(e)
                CSVExport.update_for_runs(org_id, run.created_on)
            file_number += 1



class CategoryStats(EmbeddedDocument, EmbeddedUtil):
    count = IntField()
    label = StringField()

    def __unicode__(self):
        return self.label


class Result(Document, BaseUtil):
    org = DictField()
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


class Geometry(EmbeddedDocument, EmbeddedUtil):
    type = StringField()
    coordinates = StringField()

    def __unicode__(self):
        return self.coordinates


class Boundary(Document, BaseUtil):
    org = DictField()
    created_on = DateTimeField()
    modified_on = DateTimeField()
    boundary = StringField()
    name = StringField()
    level = StringField()
    parent = StringField()
    geometry = ListField(EmbeddedDocumentField(Geometry))

    meta = {'collection': 'boundaries'}


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)