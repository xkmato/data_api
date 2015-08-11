from bson import ObjectId
from rest_framework.permissions import IsAuthenticated
from rest_framework_mongoengine.generics import RetrieveUpdateDestroyAPIView, ListAPIView
from data_api.api.models import Run, Contact, Flow, Org
from data_api.api.serializers import RunReadSerializer, ContactReadSerializer, FlowReadSerializer

__author__ = 'kenneth'


class RunList(ListAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        q = Run.objects.all()
        if self.kwargs.get('org'):
            q = Run.get_for_org(self.kwargs['org'])
        if self.request.query_params.get('ids', None):
            ids = [ObjectId(_id) for _id in self.request.query_params.get('ids')]
            q = q.filter(id__in=ids)
        return


class RunDetails(RetrieveUpdateDestroyAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()
    permission_classes = (IsAuthenticated,)


class ContactList(ListAPIView):
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if self.kwargs.get('org'):
            return Contact.get_for_org(self.kwargs['org'])
        return Contact.objects.all()


class ContactDetails(RetrieveUpdateDestroyAPIView):
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()


class FlowList(ListAPIView):
    serializer_class = FlowReadSerializer
    queryset = Flow.objects.all()

    def get_queryset(self):
        if self.kwargs.get('org'):
            return Flow.get_for_org(self.kwargs['org'])
        return Flow.objects.all()


class FlowDetails(RetrieveUpdateDestroyAPIView):
    serializer_class = FlowReadSerializer
    queryset = Flow.objects.all()
