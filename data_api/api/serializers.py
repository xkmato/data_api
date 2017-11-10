from rest_framework.fields import SerializerMethodField
from rest_framework_mongoengine import serializers
from data_api.api.models import Run, Flow, Contact, Org, Message, Broadcast, Campaign, Boundary, CampaignEvent, \
    Channel, ChannelEvent, Field, FlowStart, Group, Label

__author__ = 'kenneth'


ALWAYS_EXCLUDE = ('org_id', 'last_synced', 'first_synced')


class BaseDocumentSerializer(serializers.DocumentSerializer):
    # todo: it may be possible to remove this field?
    pass


class OrgReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Org
        exclude = ('api_token', 'is_active')


class BoundaryReadSerializer(BaseDocumentSerializer):
    class Meta:
        model = Boundary
        exclude = ALWAYS_EXCLUDE


class BroadcastReadSerializer(BaseDocumentSerializer):
    groups = SerializerMethodField()
    contacts = SerializerMethodField()

    class Meta:
        model = Broadcast
        exclude = ALWAYS_EXCLUDE + ('tid', 'urns')  # todo: why are these excluded?

    def get_groups(self, obj):
        return _serialize_list(obj.groups)

    def get_contacts(self, obj):
        return _serialize_list(obj.contacts)


class CampaignReadSerializer(BaseDocumentSerializer):
    group = SerializerMethodField()

    class Meta:
        model = Campaign
        exclude = ALWAYS_EXCLUDE

    def get_group(self, obj):
        return _serialize_doc(obj.group)


class CampaignEventReadSerializer(BaseDocumentSerializer):
    campaign = SerializerMethodField()
    flow = SerializerMethodField()

    class Meta:
        model = CampaignEvent
        exclude = ALWAYS_EXCLUDE

    def get_campaign(self, obj):
        return _serialize_doc(obj.campaign)

    def get_flow(self, obj):
        return _serialize_doc(obj.flow)


class ChannelReadSerializer(BaseDocumentSerializer):

    class Meta:
        model = Channel
        exclude = ALWAYS_EXCLUDE


class ChannelEventReadSerializer(BaseDocumentSerializer):

    class Meta:
        model = ChannelEvent
        exclude = ALWAYS_EXCLUDE


class ContactReadSerializer(BaseDocumentSerializer):
    groups = SerializerMethodField()

    class Meta:
        model = Contact
        exclude = ALWAYS_EXCLUDE

    def get_groups(self, obj):
        return _serialize_list(obj.groups)


class FieldReadSerializer(BaseDocumentSerializer):

    class Meta:
        model = Field
        exclude = ALWAYS_EXCLUDE


class FlowStartReadSerializer(BaseDocumentSerializer):

    class Meta:
        model = FlowStart
        exclude = ALWAYS_EXCLUDE


class FlowReadSerializer(BaseDocumentSerializer):
    labels = SerializerMethodField()

    class Meta:
        model = Flow
        exclude = ALWAYS_EXCLUDE

    def get_labels(self, obj):
        return _serialize_list(obj.labels)


class GroupReadSerializer(BaseDocumentSerializer):

    class Meta:
        model = Group
        exclude = ALWAYS_EXCLUDE


class LabelReadSerializer(BaseDocumentSerializer):

    class Meta:
        model = Label
        exclude = ALWAYS_EXCLUDE


class MessageReadSerializer(BaseDocumentSerializer):
    contact = SerializerMethodField()
    labels = SerializerMethodField()

    class Meta:
        model = Message
        exclude = ALWAYS_EXCLUDE

    def get_contact(self, obj):
        return _serialize_doc(obj.contact)

    def get_labels(self, obj):
        return _serialize_list(obj.labels)


class RunReadSerializer(BaseDocumentSerializer):
    contact = SerializerMethodField()
    flow = SerializerMethodField()

    class Meta:
        model = Run
        exclude = ALWAYS_EXCLUDE

    def get_contact(self, obj):
        return _serialize_doc(obj.contact)

    def get_flow(self, obj):
        return _serialize_doc(obj.flow)


def _serialize_list(doc_list, display_field='name'):
    if doc_list:
        return [_serialize_doc(doc, display_field) for doc in doc_list]
    else:
        return []


def _serialize_doc(doc, display_field='name'):
    if doc:
        return {
            'id': str(doc['id']),
            'name': doc[display_field],
        }
