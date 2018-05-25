from rest_framework import generics

from data_api.staging_api.serializers import GroupSerializer, ChannelSerializer, ContactSerializer


class OrganizationModelListView(generics.ListAPIView):

    def get_queryset(self):
        org_id = self.kwargs['org']
        return self.get_serializer_class().Meta.model.objects.filter(organization_id=org_id)


class GroupList(OrganizationModelListView):
    serializer_class = GroupSerializer


class ContactList(OrganizationModelListView):
    serializer_class = ContactSerializer


class ChannelList(OrganizationModelListView):
    serializer_class = ChannelSerializer
