from django.conf.urls import patterns, url
from data_api.api.views import RunList, RunDetails, ContactDetails, ContactList

__author__ = 'kenneth'


urlpatterns = patterns('',
                       url(r'^contacts/$', ContactList.as_view()),
                       url(r'^contacts/(?P<id>[\w]+)/$', ContactDetails.as_view()),
                       url(r'^runs/$', RunList.as_view()),
                       url(r'^runs/(?P<id>[\w]+)/$', RunDetails.as_view())
                       )
