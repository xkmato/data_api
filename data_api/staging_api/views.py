from rest_framework import generics

from data_api.staging.models import Group
from data_api.staging_api.serializers import GroupSerializer


class GroupList(generics.ListAPIView):
    serializer_class = GroupSerializer

    def get_queryset(self):
        org_id = self.kwargs['org']
        return Group.objects.filter(organization_id=org_id)
