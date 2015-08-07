from rest_framework_mongoengine.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from data_api.api.models import Run
from data_api.api.serializers import RunReadSerializer

__author__ = 'kenneth'


class RunList(ListCreateAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()


class RunDetails(RetrieveUpdateDestroyAPIView):
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()