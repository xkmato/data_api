from rest_framework.fields import SerializerMethodField
from rest_framework_mongoengine import serializers
from data_api.api.models import Run, Flow, Contact, Org, Message, Broadcast, Campaign, Boundary, CampaignEvent

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


class ContactReadSerializer(BaseDocumentSerializer):
    groups = SerializerMethodField()

    class Meta:
        model = Contact
        exclude = ALWAYS_EXCLUDE

    def get_groups(self, obj):
        return _serialize_list(obj.groups)


class FlowReadSerializer(BaseDocumentSerializer):
    labels = SerializerMethodField()

    class Meta:
        model = Flow
        exclude = ALWAYS_EXCLUDE

    def get_labels(self, obj):
        return _serialize_list(obj.labels)


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


# class FlowStepReadSerializer(serializers.EmbeddedDocumentSerializer):
#     text = SerializerMethodField()
#
#     class Meta:
#         # model = FlowStep
#         exclude = ('value',)
#
#     def get_text(self, obj):
#         if not obj.text:
#             return None
#         if obj.type == 'R':
#             return "#hidden#"
#         return FlowStepReadSerializer.remove_word_before_or_after(obj.text.lower())
#
#     @classmethod
#     def remove_word_before_or_after(cls, text):
#         x = text.split()
#         g = 'nothing'
#         if len(x) > 1:
#             if ',' in x:
#                 i = x.index(',')
#                 if i > 0 and x[i-1] not in ['hello', 'hi']:
#                     g = x.pop(i-1)
#             if 'hi' in x:
#                 i = x.index('hi')
#                 if i < len(x) -1 and x[i+1] not in [',', '.', '?']:
#                     g = x.pop(i+1)
#             if 'hello' in x:
#                 i = x.index('hello')
#                 if i < len(x) -1 and x[i+1] not in [',', '.', '?']:
#                     g = x.pop(i+1)
#         return " ".join(x).capitalize()


# class RunValueSetReadSerializer(serializers.EmbeddedDocumentSerializer):
#     category = SerializerMethodField()
#     value = SerializerMethodField('get_parsed_value')
#     rule_value = SerializerMethodField()
#
#     class Meta:
#         # model = RunValueSet
#         exclude = ('text',)
#
#     def get_category(self, obj):
#         try:
#             return eval(obj.category)
#         except Exception as e:
#             return {'base': obj.category}
#
#     def get_parsed_value(self, obj):
#         try:
#             if hasattr(obj, 'category') and obj.category:
#                 category = eval(obj.category)
#                 if 'eng' in category and category['eng'] == "All Responses":
#                     return None
#                 if 'base' in category and category['base'] == "All Responses":
#                     return None
#             return obj.value
#         except Exception as e:
#             if obj.category == "All Responses":
#                 return None
#             return obj.value
#
#     def get_rule_value(self, obj):
#         try:
#             if hasattr(obj, 'category') and obj.category:
#                 category = eval(obj.category)
#                 if 'eng' in category and category['eng'] == "All Responses":
#                     return None
#                 if 'base' in category and category['base'] == "All Responses":
#                     return None
#             return obj.rule_value
#         except Exception as e:
#             if obj.category == "All Responses":
#                 return None
#             return obj.rule_value


# class EventReadSerializer(BaseDocumentSerializer):
#     flow = SerializerMethodField()
#     campaign = SerializerMethodField()
#
#     class Meta:
#         # model = Event
#         exclude = ALWAYS_EXCLUDE
#
#     def get_flow(self, obj):
#         return str(obj.flow.get('id', '')) or None
#
#     def get_campaign(self, obj):
#         return str(obj.campaign.get('id', '')) or None


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
