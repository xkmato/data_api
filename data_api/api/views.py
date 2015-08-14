from bson import ObjectId
from rest_framework.permissions import IsAuthenticated
from rest_framework_mongoengine.generics import ListAPIView, RetrieveAPIView
from data_api.api.models import Run, Contact, Flow, Org, Message
from data_api.api.permissions import ContactAccessPermissions
from data_api.api.serializers import RunReadSerializer, ContactReadSerializer, FlowReadSerializer, OrgReadSerializer, \
    MessageReadSerializer

__author__ = 'kenneth'


class DataListAPIView(ListAPIView):
    def get_queryset(self):
        q = self.object_model.objects.all()
        if self.kwargs.get('org'):
            q = self.object_model.get_for_org(self.kwargs['org'])
        if self.request.query_params.get('ids', None):
            ids = [ObjectId(_id) for _id in self.request.query_params.get('ids')]
            q = q.filter(id__in=ids)
        if self.request.query_params.get('after', None):
            q = q.filter(created_on=self.request.query_params.get('after'))
        return q


class RunList(DataListAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()
    permission_classes = (IsAuthenticated,)
    object_model = Run

    def get_queryset(self):
        q = super(RunList, self).get_queryset()
        if self.kwargs.get('flow'):
            q = q.filter(flow__id=ObjectId(self.kwargs.get('flow')))
        return q


class RunDetails(RetrieveAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()
    permission_classes = (IsAuthenticated,)


class ContactList(DataListAPIView):
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()
    permission_classes = (IsAuthenticated, ContactAccessPermissions)
    object_model = Contact


class ContactDetails(RetrieveAPIView):
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()
    permission_classes = (IsAuthenticated, ContactAccessPermissions)


class FlowList(DataListAPIView):
    serializer_class = FlowReadSerializer
    object_model = Flow


class FlowDetails(RetrieveAPIView):
    serializer_class = FlowReadSerializer
    queryset = Flow.objects.all()


class OrgList(ListAPIView):
    serializer_class = OrgReadSerializer
    queryset = Org.objects.all()


class OrgDetails(RetrieveAPIView):
    serializer_class = OrgReadSerializer
    queryset = Org.objects.all()


class MessageList(DataListAPIView):
    serializer_class = MessageReadSerializer
    object_model = Message


class MessageDetails(RetrieveAPIView):
    serializer_class = MessageReadSerializer
    queryset = MessageReadSerializer


