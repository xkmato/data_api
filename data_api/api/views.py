from bson import ObjectId
from mongoengine.django.shortcuts import get_document_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework_mongoengine.generics import ListAPIView, RetrieveAPIView
from data_api.api.models import Run, Contact, Flow, Org, Message, Broadcast, Campaign, Event
from data_api.api.permissions import ContactAccessPermissions
from data_api.api.serializers import RunReadSerializer, ContactReadSerializer, FlowReadSerializer, OrgReadSerializer, \
    MessageReadSerializer, BroadcastReadSerializer, CampaignReadSerializer, EventReadSerializer

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
        if self.kwargs.get('flow_uuid'):
            flow = get_document_or_404(Flow.objects.all(), uuid=self.kwargs.get('flow_uuid'))
            return q.filter(flow__id=flow.id)
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

    def get_object(self):
        if self.kwargs.get('uuid', None):
            return get_document_or_404(self.get_queryset(), uuid=self.kwargs.get('uuid'))
        return super(FlowDetails, self).get_object()


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
    queryset = Message


class BroadcastList(DataListAPIView):
    serializer_class = BroadcastReadSerializer
    object_model = Broadcast


class BroadcastDetails(RetrieveAPIView):
    serializer_class = BroadcastReadSerializer
    queryset = Broadcast


class CampaignList(DataListAPIView):
    serializer_class = CampaignReadSerializer
    object_model = Campaign


class CampaignDetails(RetrieveAPIView):
    serializer_class = CampaignReadSerializer
    queryset = Campaign


class EventList(DataListAPIView):
    serializer_class = EventReadSerializer
    object_model = Event


class EventDetails(RetrieveAPIView):
    serializer_class = EventReadSerializer
    queryset = Event

