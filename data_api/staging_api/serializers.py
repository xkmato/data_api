from rest_framework import serializers

from data_api.staging.models import Group, Channel, Device, Contact, ChannelEvent, Field, Broadcast, Campaign, \
    Flow, CampaignEvent, Label, FlowStart, Run, Boundary


def RapidproIdField():
    return serializers.IntegerField(source='rapidpro_id')


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = '__all__'


class ContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contact
        fields = '__all__'


class ChannelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Channel
        fields = '__all__'


class ChannelEventSerializer(serializers.ModelSerializer):
    id = RapidproIdField()

    class Meta:
        model = ChannelEvent
        fields = '__all__'


class DeviceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Device
        fields = '__all__'


class FieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = Field
        fields = '__all__'


class BroadcastSerializer(serializers.ModelSerializer):

    class Meta:
        model = Broadcast
        fields = '__all__'


class CampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = Campaign
        fields = '__all__'


class CampaignEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampaignEvent
        fields = '__all__'


class LabelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Label
        fields = '__all__'


class FlowSerializer(serializers.ModelSerializer):

    class Meta:
        model = Flow
        fields = '__all__'


class FlowStartSerializer(serializers.ModelSerializer):

    class Meta:
        model = FlowStart
        fields = '__all__'


class RunSerializer(serializers.ModelSerializer):
    id = RapidproIdField()

    class Meta:
        model = Run
        fields = '__all__'


class BoundarySerializer(serializers.ModelSerializer):

    class Meta:
        model = Boundary
        fields = '__all__'
