from rest_framework_mongoengine import serializers
from data_api.api.models import Run, Flow, Contact

__author__ = 'kenneth'


class RunReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Run
        depth = 3


class FlowReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Flow
        depth = 3


class ContactReadSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Contact
        depth = 3