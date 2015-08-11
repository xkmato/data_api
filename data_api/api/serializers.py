from rest_framework.fields import SerializerMethodField
from rest_framework_mongoengine import serializers
from data_api.api.models import Run, Flow, Contact, FlowStep, RunValueSet, Org

__author__ = 'kenneth'


class OrgReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Org
        fields = ('name', )


class FlowStepReadSerializer(serializers.EmbeddedDocumentSerializer):
    class Meta:
        model = FlowStep
        exclude = ('text',)


class RunValueSetReadSerializer(serializers.EmbeddedDocumentSerializer):
    class Meta:
        model = RunValueSet
        exclude = ('text',)


class ContactReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'uuid', 'groups', 'fields', 'language')


class RunReadSerializer(serializers.DocumentSerializer):
    values = RunValueSetReadSerializer(many=True)
    steps = FlowStepReadSerializer(many=True)
    contact_id = SerializerMethodField()
    flow_id = SerializerMethodField()
    org_id = SerializerMethodField()

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
        return unicode(obj.contact['id'])

    def get_flow_id(self, obj):
        return unicode(obj.flow['id'])

    def get_org_id(self, obj):
        return unicode(obj.org['id'])


class FlowReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Flow
        depth = 3
