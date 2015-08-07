from datetime import datetime
from django.conf import settings
from mongoengine import connect, Document, StringField, BooleanField, ReferenceField, DateTimeField, IntField, \
    EmbeddedDocument, ListField, EmbeddedDocumentField, DictField, DynamicDocument
from temba import TembaClient
from temba.base import TembaNoSuchObjectError, TembaException

__author__ = 'kenneth'

connect(db="rapidpro1")


class Org(Document):
    name = StringField(required=True)
    language = StringField()
    timezone = StringField(default="UTC")
    api_token = StringField(required=True)
    is_active = BooleanField(default=False)
    meta = {'collection': 'orgs'}

    @classmethod
    def create(cls, **kwargs):
        org = cls()
        for k,v in kwargs.items():
            setattr(org, k, v)
        org.save()
        return org

    def get_temba_client(self):
        host = getattr(settings, 'SITE_API_HOST', None)
        agent = getattr(settings, 'SITE_API_USER_AGENT', None)

        if not host:
            host = '%s/api/v1' % settings.API_ENDPOINT  # UReport sites use this

        return TembaClient(host, self.api_token, user_agent=agent)


class LastSaved(DynamicDocument):
    coll = StringField()
    org = ReferenceField(Org)
    last_saved = DateTimeField()


class BaseUtil(object):
    @classmethod
    def create_from_temba(cls, org, temba):
        obj = cls()
        obj.org = org
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
        func = "get_%s" % cls.meta['collection']
        fetch = getattr(org.get_temba_client(), func.rstrip('s'))
        return cls.create_from_temba(org, fetch(uuid))

    @classmethod
    def create_from_temba_list(cls, org, temba_list):
        print temba_list
        obj_list = []
        q = None
        for temba in temba_list:
            if hasattr(temba, 'uuid'):
                q = {'uuid': temba.uuid}
            elif hasattr(temba, 'id'):
                q = {'tid': temba.id}
            if not q or not cls.objects.filter(**q).exists():
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
        func = "get_%s" % cls.meta['collection']
        ls = LastSaved.objects.filter(**{'coll': cls.meta['collection'], 'org.id': org.id}).first()
        after = getattr(ls, 'last_saved', None)
        fetch_all = getattr(org.get_temba_client(), func)
        try:
            objs = cls.create_from_temba_list(org, fetch_all(after=after, pager=pager))
            if not ls:
                ls = LastSaved()
                ls.org = org
            ls.coll = cls.meta['collection']
            ls.last_saved = datetime.now(tz=org.timezone)
            ls.save()
        except TypeError:
            try:
                objs = cls.create_from_temba_list(org, fetch_all(pager=pager))
            except TypeError:
                objs = cls.create_from_temba_list(org, fetch_all())
        return objs


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
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
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


class Contact(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    urns = ListField(EmbeddedDocumentField(Urn))
    groups = ListField(ReferenceField(Group))
    language = StringField()
    fields = DictField()

    meta = {'collection': 'contacts'}


class Broadcast(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    tid = IntField()
    urns = ListField(EmbeddedDocumentField(Urn))
    contacts = ListField(ReferenceField(Contact))
    groups = ListField(ReferenceField(Group))
    text = StringField()
    status = StringField()

    meta = {'collection': 'broadcasts'}


class Campaign(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    group = ReferenceField(Group)

    meta = {'collection': 'campaigns'}


class Ruleset(EmbeddedDocument, EmbeddedUtil):
    uuid = StringField()
    label = StringField()
    response_type = StringField()


class Label(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    count = IntField()

    meta = {'collection': 'labels'}


class Flow(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    uuid = StringField()
    name = StringField()
    archived = StringField()
    labels = ListField(ReferenceField(Label))
    participants = IntField()
    runs = IntField()
    completed_runs = IntField()
    rulesets = ListField(EmbeddedDocumentField(Ruleset))

    meta = {'collection': 'flows'}


class Event(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    uuid = StringField()
    campaign = ReferenceField(Campaign)
    relative_to = StringField()
    offset = IntField()
    unit = StringField()
    delivery_hour = IntField()
    message = StringField()
    flow = ReferenceField(Flow)

    meta = {'collection': 'events'}


class Message(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    tid = IntField()
    broadcast = ReferenceField(Broadcast)
    contact = ReferenceField(Contact)
    urn = EmbeddedDocumentField(Urn)
    status = StringField()
    type = StringField()
    labels = ListField(ReferenceField(Label))
    direction = StringField()
    archived = StringField()
    text = StringField()
    delivered_on = DateTimeField()
    sent_on = DateTimeField()

    meta = {'collection': 'messages'}
    

class RunValueSet(EmbeddedDocument, EmbeddedUtil):
    node = StringField()
    category = StringField()
    text = StringField()
    rule_value = StringField()
    label = StringField()
    value = StringField()
    time = DateTimeField()
    

class FlowStep(EmbeddedDocument, EmbeddedUtil):
    node = StringField()
    text = StringField()
    value = StringField()
    type = StringField()
    arrived_on = DateTimeField()
    left_on = DateTimeField()
    

class Run(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    tid = IntField()
    flow = ReferenceField(Flow)
    contact = ReferenceField(Contact)
    steps = ListField(EmbeddedDocumentField(FlowStep))
    values = ListField(EmbeddedDocumentField(RunValueSet))
    completed = StringField()

    meta = {'collection': 'runs'}
    

class CategoryStats(EmbeddedDocument, EmbeddedUtil):
    count = IntField()
    label = StringField()
    

class Result(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    boundary = StringField()
    set = IntField()
    unset = IntField()
    open_ended = StringField()
    label = StringField()
    categories = ListField(EmbeddedDocumentField(CategoryStats))

    meta = {'collection': 'results'}
    

class Geometry(EmbeddedDocument, EmbeddedUtil):
    type = StringField()
    coordinates = StringField()
    

class Boundary(Document, BaseUtil):
    org = ReferenceField(Org)
    created_on = DateTimeField(default=datetime.now)
    modified_on = DateTimeField()
    boundary = StringField()
    name = StringField()
    level = StringField()
    parent = StringField()
    geometry = ListField(EmbeddedDocumentField(Geometry))

    meta = {'collection': 'boundaries'}