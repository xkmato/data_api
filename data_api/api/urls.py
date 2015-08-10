from django.conf.urls import patterns, url
from data_api.api.views import RunList, RunDetails

__author__ = 'kenneth'


urlpatterns = patterns('',
                       url(r'^runs/$', RunList.as_view()),
                       url(r'^runs/(?P<id>[\w])/$', RunDetails.as_view())
                       )
