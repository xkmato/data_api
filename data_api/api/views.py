from rest_framework_mongoengine.generics import RetrieveUpdateDestroyAPIView, ListAPIView
from data_api.api.models import Run, Contact
from data_api.api.serializers import RunReadSerializer, ContactReadSerializer

__author__ = 'kenneth'


class RunList(ListAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()


class RunDetails(RetrieveUpdateDestroyAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()


class ContactList(ListAPIView):
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()


class ContactDetails(RetrieveUpdateDestroyAPIView):
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()
