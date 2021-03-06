from django.conf.urls import patterns, url
from data_api.api.views import RunList, RunDetails, ContactDetails, ContactList, FlowList, FlowDetails, OrgDetails, \
    OrgList, MessageList, MessageDetails, BroadcastList, BroadcastDetails, CampaignDetails, CampaignList, EventList, \
    EventDetails

__author__ = 'kenneth'


urlpatterns = patterns('',
                       url(r'^broadcasts/$', BroadcastList.as_view()),
                       url(r'^broadcasts/org/(?P<org>[\w]+)/$', BroadcastList.as_view()),
                       url(r'^broadcasts/(?P<id>[\w]+)/$', BroadcastDetails.as_view()),

                       url(r'^campaigns/$', CampaignList.as_view()),
                       url(r'^campaigns/org/(?P<org>[\w]+)/$', CampaignList.as_view()),
                       url(r'^campaigns/(?P<id>[\w]+)/$', CampaignDetails.as_view()),

                       url(r'^contacts/$', ContactList.as_view()),
                       url(r'^contacts/org/(?P<org>[\w]+)/$', ContactList.as_view()),
                       url(r'^contacts/(?P<id>[\w]+)/$', ContactDetails.as_view()),

                       url(r'^events/$', EventList.as_view()),
                       url(r'^events/org/(?P<org>[\w]+)/$', EventList.as_view()),
                       url(r'^events/(?P<id>[\w]+)/$', EventDetails.as_view()),

                       url(r'^flows/$', FlowList.as_view()),
                       url(r'^flows/org/(?P<org>[\w]+)/$', FlowList.as_view()),
                       url(r'^flows/uuid/(?P<uuid>[\w\-]+)/$', FlowDetails.as_view()),
                       url(r'^flows/(?P<id>[\w]+)/$', FlowDetails.as_view()),

                       url(r'^messages/$', MessageList.as_view()),
                       url(r'^messages/org/(?P<org>[\w]+)/$', MessageList.as_view()),
                       url(r'^messages/(?P<id>[\w]+)/$', MessageDetails.as_view()),

                       url(r'^orgs/$', OrgList.as_view()),
                       url(r'^orgs/(?P<id>[\w]+)/$', OrgDetails.as_view()),

                       url(r'^runs/$', RunList.as_view()),
                       url(r'^runs/org/(?P<org>[\w]+)/$', RunList.as_view()),
                       url(r'^runs/flow/(?P<flow>[\w]+)/$', RunList.as_view()),
                       url(r'^runs/flow_uuid/(?P<flow_uuid>[\w\-]+)/$', RunList.as_view()),
                       url(r'^runs/(?P<id>[\w]+)/$', RunDetails.as_view()),
                       )
