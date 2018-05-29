from rest_framework import generics

from data_api.staging_api.serializers import GroupSerializer, ChannelSerializer, ContactSerializer, \
    ChannelEventSerializer, FieldSerializer, BroadcastSerializer, CampaignSerializer, FlowSerializer, \
    CampaignEventSerializer


class OrganizationModelListView(generics.ListAPIView):

    def get_queryset(self):
        org_id = self.kwargs['org']
        return self.get_serializer_class().Meta.model.objects.filter(organization_id=org_id)


class GroupList(OrganizationModelListView):
    serializer_class = GroupSerializer


class ContactList(OrganizationModelListView):
    serializer_class = ContactSerializer


class FieldList(OrganizationModelListView):
    serializer_class = FieldSerializer


class ChannelList(OrganizationModelListView):
    serializer_class = ChannelSerializer


class ChannelEventList(OrganizationModelListView):
    serializer_class = ChannelEventSerializer


class BroadcastList(OrganizationModelListView):
    serializer_class = BroadcastSerializer


class CampaignList(OrganizationModelListView):
    serializer_class = CampaignSerializer


class CampaignEventList(OrganizationModelListView):
    serializer_class = CampaignEventSerializer


class FlowList(OrganizationModelListView):
    serializer_class = FlowSerializer


