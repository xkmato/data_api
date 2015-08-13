from django.conf.urls import patterns, url
from data_api.api.views import RunList, RunDetails, ContactDetails, ContactList, FlowList, FlowDetails, OrgDetails, \
    OrgList

__author__ = 'kenneth'


urlpatterns = patterns('',
                       url(r'^contacts/$', ContactList.as_view()),
                       url(r'^contacts/org/(?P<org>[\w]+)/$', ContactList.as_view()),
                       url(r'^contacts/(?P<id>[\w]+)/$', ContactDetails.as_view()),

                       url(r'^flows/$', FlowList.as_view()),
                       url(r'^flows/org/(?P<org>[\w]+)/$', FlowList.as_view()),
                       url(r'^flows/(?P<id>[\w]+)/$', FlowDetails.as_view()),

                       url(r'^runs/$', RunList.as_view()),
                       url(r'^runs/org/(?P<org>[\w]+)/$', RunList.as_view()),
                       url(r'^runs/(?P<id>[\w]+)/$', RunDetails.as_view()),

                       url(r'^orgs/$', OrgList.as_view()),
                       url(r'^orgs/(?P<id>[\w]+)/$', OrgDetails.as_view())
                       )
