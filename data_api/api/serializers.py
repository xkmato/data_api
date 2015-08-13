from rest_framework.fields import SerializerMethodField
from rest_framework_mongoengine import serializers
from data_api.api.models import Run, Flow, Contact, FlowStep, RunValueSet, Org, Message

__author__ = 'kenneth'


class OrgReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Org
        fields = ('name', 'id', 'timezone')


class FlowStepReadSerializer(serializers.EmbeddedDocumentSerializer):
    text = SerializerMethodField()

    class Meta:
        model = FlowStep

    def get_text(self, obj):
        if not obj.text:
            return None
        return FlowStepReadSerializer.remove_word_before_or_after(obj.text.lower())

    @classmethod
    def remove_word_before_or_after(cls, text):
        x = text.split()
        g = 'nothing'
        if len(x) > 1:
            if ',' in x:
                i = x.index(',')
                if i > 0 and x[i-1] not in ['hello', 'hi']:
                    g = x.pop(i-1)
            if 'hi' in x:
                i = x.index('hi')
                if i < len(x) -1 and x[i+1] not in [',', '.', '?']:
                    g = x.pop(i+1)
        return " ".join(x)


class RunValueSetReadSerializer(serializers.EmbeddedDocumentSerializer):
    category = SerializerMethodField()

    class Meta:
        model = RunValueSet
        exclude = ('text',)

    def get_category(self, obj):
        try:
            return eval(obj.category)
        except Exception as e:
            print e
            return {}


class ContactReadSerializer(serializers.DocumentSerializer):
    org_id = SerializerMethodField()
    groups = SerializerMethodField()
    contact_fields = SerializerMethodField('get_eval_fields')

    class Meta:
        model = Contact
        fields = ('id', 'groups', 'contact_fields', 'language', 'org_id')

    def get_org_id(self, obj):
        if obj.org:
            return unicode(obj.org['id'])
        return None

    def get_groups(self, obj):
        if obj.groups:
            return [g['name'] for g in obj.groups]
        return []

    def get_eval_fields(self, obj):
        return eval(obj.fields)


class RunReadSerializer(serializers.DocumentSerializer):
    values = RunValueSetReadSerializer(many=True)
    steps = FlowStepReadSerializer(many=True)
    contact_id = SerializerMethodField()
    flow_id = SerializerMethodField()
    org_id = SerializerMethodField()
    completed = SerializerMethodField()

    class Meta:
        model = Run
        depth = 3
        exclude = ('tid', 'modified_on', 'contact', 'flow', 'org')

    def update(self, instance, validated_data):
        values = validated_data.pop('values')
        steps = validated_data.pop('steps')
        updated_instance = super(RunReadSerializer, self).update(instance, validated_data)

        for value_data in values:
            updated_instance.values.append(RunValueSet(**value_data))

        for step_data in steps:
            updated_instance.steps.append(FlowStep(**step_data))

        updated_instance.save()
        return updated_instance

    def get_contact_id(self, obj):
        if obj.contact.has_key("id"):
            return unicode(obj.contact['id'])
        return None

    def get_flow_id(self, obj):
        if obj.flow.has_key("id"):
            return unicode(obj.flow['id'])
        return None

    def get_org_id(self, obj):
        if obj.org:
            if obj.org.has_key("id"):
                return unicode(obj.org['id'])
        return None

    def get_completed(self, obj):
        return eval(obj.completed)


class FlowReadSerializer(serializers.DocumentSerializer):
    org_id = SerializerMethodField()

    class Meta:
        model = Flow
        depth = 3
        exclude = ('org', 'modified_on',)

    def get_org_id(self, obj):
        if obj.org:
            if obj.org.has_key("id"):
                return unicode(obj.org['id'])
        return None


class MessageReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Message
