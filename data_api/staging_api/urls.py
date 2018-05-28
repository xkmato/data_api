from django.conf.urls import patterns, url

from data_api.staging_api.views import GroupList, ChannelList, ContactList, ChannelEventList, FieldList, \
    BroadcastList

urlpatterns = patterns(
    '',
    # url(r'^boundaries/org/(?P<org>[\w]+)/$', BoundaryList.as_view()),
    #
    # url(r'^broadcasts/$', BroadcastList.as_view()),
    url(r'^broadcasts/org/(?P<org>[\w]+)/$', BroadcastList.as_view()),
    # url(r'^broadcasts/(?P<id>[\w]+)/$', BroadcastDetails.as_view()),
    #
    # url(r'^campaigns/$', CampaignList.as_view()),
    # url(r'^campaigns/org/(?P<org>[\w]+)/$', CampaignList.as_view()),
    # url(r'^campaigns/(?P<id>[\w]+)/$', CampaignDetails.as_view()),
    #
    # url(r'^campaign_events/org/(?P<org>[\w]+)/$', CampaignEventList.as_view()),
    #
    url(r'^channels/org/(?P<org>[\w]+)/$', ChannelList.as_view()),

    url(r'^channel_events/org/(?P<org>[\w]+)/$', ChannelEventList.as_view()),

    # url(r'^contacts/$', ContactList.as_view()),
    url(r'^contacts/org/(?P<org>[\w]+)/$', ContactList.as_view()),
    # url(r'^contacts/(?P<id>[\w]+)/$', ContactDetails.as_view()),
    #
    url(r'^fields/org/(?P<org>[\w]+)/$', FieldList.as_view()),

    # url(r'^flow_starts/org/(?P<org>[\w]+)/$', FlowStartList.as_view()),
    #
    # url(r'^flows/$', FlowList.as_view()),
    # url(r'^flows/org/(?P<org>[\w]+)/$', FlowList.as_view()),
    # url(r'^flows/uuid/(?P<uuid>[\w\-]+)/$', FlowDetails.as_view()),
    # url(r'^flows/(?P<id>[\w]+)/$', FlowDetails.as_view()),

    url(r'^groups/org/(?P<org>[\w]+)/$', GroupList.as_view()),
    # url(r'^labels/org/(?P<org>[\w]+)/$', LabelList.as_view()),

    # url(r'^messages/$', MessageList.as_view()),
    # url(r'^messages/org/(?P<org>[\w]+)/$', MessageList.as_view()),
    # url(r'^messages/(?P<id>[\w]+)/$', MessageDetails.as_view()),

    # url(r'^orgs/$', OrgList.as_view()),
    # url(r'^orgs/(?P<id>[\w]+)/$', OrgDetails.as_view()),

    # url(r'^runs/$', RunList.as_view()),
    # url(r'^runs/org/(?P<org>[\w]+)/$', RunList.as_view()),
    # url(r'^runs/flow/(?P<flow>[\w]+)/$', RunList.as_view()),
    # url(r'^runs/flow_uuid/(?P<flow_uuid>[\w\-]+)/$', RunList.as_view()),
    # url(r'^runs/(?P<id>[\w]+)/$', RunDetails.as_view()),
    #
    # url(r'^resthooks/org/(?P<org>[\w]+)/$', ResthookList.as_view()),
    # url(r'^resthook_events/org/(?P<org>[\w]+)/$', ResthookEventList.as_view()),
    # url(r'^resthook_subscribers/org/(?P<org>[\w]+)/$', ResthookSubscriberList.as_view()),
)
