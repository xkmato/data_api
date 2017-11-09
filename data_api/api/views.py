from bson import ObjectId
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework_mongoengine.generics import ListAPIView, RetrieveAPIView
from data_api.api.models import Run, Contact, Flow, Org, Message, Broadcast, Campaign
from data_api.api.permissions import ContactAccessPermissions, MessageAccessPermissions, OrgAccessPermissions
from data_api.api.serializers import RunReadSerializer, ContactReadSerializer, FlowReadSerializer, OrgReadSerializer, \
    MessageReadSerializer, BroadcastReadSerializer, CampaignReadSerializer
from data_api.api.utils import get_date_from_param
from data_api.mongo_utils.shortcuts import get_document_or_404

__author__ = 'kenneth'


class DataListAPIView(ListAPIView):
    def get_queryset(self):
        if not self.kwargs.get('org'):
            return self.object_model.objects.none()
        q = self.object_model.objects.all()
        if self.kwargs.get('org'):
            q = self.object_model.get_for_org(self.kwargs['org'])
        if self.request.query_params.get('ids', None):
            ids = [ObjectId(_id) for _id in self.request.query_params.get('ids')]
            q = q.filter(id__in=ids)
        if self.request.query_params.get('after', None):
            q = q.filter(created_on__gt=get_date_from_param(self.request.query_params.get('after')))
        if self.request.query_params.get('before', None):
            q = q.filter(created_on__lt=get_date_from_param(self.request.query_params.get('before')))
        return q


class RunList(DataListAPIView):
    """
    This endpoint allows you to list Runs.

    ## Filters

    You can use the filters below in the url query string(```?filter=value```) to filter the data

    * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)
    * **before** - Return results with ```created_on``` date before (digit) (format ``ddmmyyyy``)
    * **after** - Return results with ```created_on``` date after (digit) (format ``ddmmyyyy``)

    ## Listing Runs

    By making a ```GET``` request you can list all the runs, filtering them as needed.  Each
    run has the following attributes:

    * **id** - the ID of the poll (int)
    * **org_id** - the ID of the org to which the run belongs(string) (filterable: ```org```)
    * **values** - the VALUES of this run (list(dictionary))
    * **steps** - the STEPS of this run (list(dictionary))
    * **contact_id** - the ID of the contact participating in this run (string)
    * **flow_id** - this ID of the flow to which this run belongs (string)
    * **completed** - the COMPLETED flag shows if the run was completed or not (boolean)
    * **created_on** - the TIME when this run was created (datetime) (filterable: ```before``` and ```after``` - format: ```ddmmyyyy```)

    Examples:

        GET /api/v1/runs/org/xxxxxxxxxxxxx/
        GET /api/v1/runs/flow/xxxxxxxxxxxxx/
        GET /api/v1/runs/flow_uuid/xxxxxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxx/
        GET /api/v1/runs/?after=13012016&before=15012016

    Response is the list of runs on the flow, most recent first:

        {
            "count": 389,
            "next": "/api/v1/runs/?page=1",
            "previous": null,
            "results": [
            {
                "id": "xxxxxxxxxxxxxxxxxxxxxxxxx",
                "values": [],
                "steps": [
                    {
                        "text": "Hello world",
                        "node": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx",
                        "type": "A",
                        "arrived_on": "2015-07-28T19:10:47.441000",
                        "left_on": "2015-07-28T19:10:47.675000"
                    },
                    {
                        "text": null,
                        "node": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx",
                        "type": "R",
                        "arrived_on": "2015-07-28T19:10:47.675000",
                        "left_on": null
                    }
                ],
                "contact_id": "xxxxxxxxxxxxxxxxxxxxxxxxx",
                "flow_id": "xxxxxxxxxxxxxxxxxxxxxxxxx",
                "org_id": "xxxxxxxxxxxxxxxxxxxxxxxxx",
                "completed": false,
                "created_on": "2015-07-28T19:10:47.431000"
            },
            ...
        }
    """
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
        return q.filter(flow__id__ne=ObjectId(settings.EXCLUDED_FLOWS))


class RunDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Run.

    Example:

        GET /api/v1/runs/xxxxxxxxxxxxx/
    """
    serializer_class = RunReadSerializer
    queryset = Run.objects.all()
    permission_classes = (IsAuthenticated,)


class ContactList(DataListAPIView):
    """
    This endpoint allows you to list Contacts.

    ## Filters

    You can use the filters below in the url query string(```?filter=value```) to filter the data

    * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)

    ## Listing Contacts

    By making a ```GET``` request you can list all the Contacts, filtering them as needed.  Each
    flow has the following attributes:

    * **id** - the ID of the poll (int)
    * **org_id** - the ID of the org to which the run belongs(string) (filterable: ```org```)
    * **groups** - the GROUPS to which the contact belongs (list(dictionary))
    * **contact_fields** - the extra FIELDS for this contact (dictionary)
    * **language** - the preferred LANGUAGE for this contact (string)

    Examples:

        GET /api/v1/contacts/org/xxxxxxxxxxxxx/

    Response is the list of contacts, most recent first:

        {
            "count": 389,
            "next": "/api/v1/contacts/?page=1",
            "previous": null,
            "results": [
            {
                "id": "xxxxxxxxxxxxx",
                "groups": [],
                "contact_fields": {
                    "last_menses_date": null,
                    "reseaux_nombre": null,
                    "contact_nom_site": null,
                },
                "language": null,
                "org_id": "xxxxxxxxxxxxx"
            },
            ...
        }
    """
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()
    permission_classes = (IsAuthenticated, ContactAccessPermissions)
    object_model = Contact


class ContactDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Contact.

    Example:

        GET /api/v1/contacts/xxxxxxxxxxxxx/
    """
    serializer_class = ContactReadSerializer
    queryset = Contact.objects.all()
    permission_classes = (IsAuthenticated, ContactAccessPermissions)


class FlowList(DataListAPIView):
    """
    This endpoint allows you to list Flows.

    ## Filters

    You can use the filters below in the url query string(```?filter=value```) to filter the data

    * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)
    * **before** - Return results with ```created_on``` date before (digit) (format ``ddmmyyyy``)
    * **after** - Return results with ```created_on``` date after (digit) (format ``ddmmyyyy``)

    ## Listing Flows

    By making a ```GET``` request you can list all the flows, filtering them as needed.  Each
    flow has the following attributes:

    * **id** - the ID of the poll (int)
    * **org_id** - the ID of the org to which the flow belongs(string) (filterable: ```org```)
    * **created_on** - the CREATE DATE of the flow (date) (filterable: ```before``` and ```after``` - format: ```ddmmyyyy```)
    * **uuid** - the UUID of the flow as is in rapidpro (string)
    * **name** - the NAME of of this flow (string)
    * **archived** - this flag shows whether the flow is archived or not (boolean)
    * **labels** - the LABELS attached to this flow (list(string))
    * **participants** - the number of PARTICIPANTS in this flow (int)
    * **runs** - the number of runs in this flow so far (int)
    * **completed_runs** - the number of complete runs in this flow so far (int)
    * **rulesets** - the RULESETS of this flow (list(dictionary))

    Examples:

        GET /api/v1/flows/org/xxxxxxxxxxxxx/
        GET /api/v1/flows/?after=13012016&before=15012016

    Response is the list flows, most recent first:

        {
            "count": 389,
            "next": "/api/v1/flows/?page=1",
            "previous": null,
            "results": [
            {
                "id": "xxxxxxxxxxxx",
                "org_id": "xxxxxxxxxxxxx",
                "created_on": "2015-02-16T06:38:04.990000",
                "uuid": "xxxxxx-xxxx-xxxx-xxxx-xxxxxxxx",
                "name": "SAMPLE FLOW",
                "archived": true,
                "labels": [
                    null
                ],
                "participants": 21,
                "runs": 49,
                "completed_runs": 22,
                "rulesets": [
                    {
                        "label": "Sample Response",
                        "uuid": "xxxxxxx-xxx-xxx-xxx-xxxxxxxxx",
                        "response_type": "O"
                    },
                ]
            },
            ...
        }
    """
    serializer_class = FlowReadSerializer
    object_model = Flow


class FlowDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Flow.

    Examples:

        GET /api/v1/flows/uuid/xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx/
        GET /api/v1/flows/xxxxxxxxxxxxx/
    """
    serializer_class = FlowReadSerializer
    queryset = Flow.objects.all()

    def get_object(self):
        if self.kwargs.get('uuid', None):
            return get_document_or_404(self.get_queryset(), uuid=self.kwargs.get('uuid'))
        return super(FlowDetails, self).get_object()


class OrgList(ListAPIView):
    """
    This endpoint allows you to list Orgs.

    ## Listing Orgs

    By making a ```GET``` request you can list all the Orgs, filtering them as needed.  Each
    flow has the following attributes:

    * **id** - the ID of the org (int)
    * **name** - the NAME of the org(string)
    * **timezone** - the TIMEZONE of the Org (timezone)

    Examples:

        GET /api/v1/orgs/

    Response is the list of orgs, most recent first:

        {
            "count": 389,
            "next": "/api/v1/orgs/?page=1",
            "previous": null,
            "results": [
            {
                "name": "Uganda",
                "id": "xxxxxxxxxxxxx",
                "timezone": "Africa/Kampala"
            },
            ...
        }
    """
    serializer_class = OrgReadSerializer
    queryset = Org.objects.all()
    permission_classes = (IsAuthenticated, OrgAccessPermissions)


class OrgDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Org.

    Example:

        GET /api/v1/orgs/xxxxxxxxxxxxx/
    """
    serializer_class = OrgReadSerializer
    queryset = Org.objects.all()


class MessageList(DataListAPIView):
    """
    This endpoint allows you to list Messages.

    ## Filters

    You can use the filters below in the url query string(```?filter=value```) to filter the data

    * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)
    * **before** - Return results with ```created_on``` date before (digit) (format ``ddmmyyyy``)
    * **after** - Return results with ```created_on``` date after (digit) (format ``ddmmyyyy``)

    ## Listing Messages

    By making a ```GET``` request you can list all the Messages, filtering them as needed.  Each
    flow has the following attributes:

    * **id** - the ID of the poll (int)
    * **org_id** - the ID of the org to which the flow belongs(string) (filterable: ```org```)
    * **broadcast** - the ID of the broadcast if this message was part of a broadcast (date)
    * **contact** - the ID of the contact related to this message (string)
    * **labels** - the LABELS of this message (list(string))
    * **created_on** - this DATE on which this message was created (datetime) (filterable: ```before``` and ```after``` - format: ```ddmmyyyy```)
    * **status** - the STATUS of this message (string)
    * **type** - the TYPE of this message (string)
    * **direction** - the DIRECTION of this message (string)
    * **archived** - a flag that shows whether the message is archived or not (boolean)
    * **text** - the TEXT content of this message (string)
    * **delivered_on** - the DATE when this message was delivered (datetime)
    * **sent_on** - the DATE when this message was sent (datetime)

    Examples:

        GET /api/v1/messages/org/xxxxxxxxxxxxx/

    Response is the list flows, most recent first:

        {
            "count": 389,
            "next": "/api/v1/flows/?page=1",
            "previous": null,
            "results": [
            {
              "id": "",
              "org_id": "",
              "broadcast": "",
              "contact": "",
              "labels": "",
              "created_on": "",
              "status": "",
              "type": "",
              "direction": "",
              "archived": "",
              "text": "",
              "delivered_on": "",
              "sent_on": ""
            },
            ...
        }
    """
    serializer_class = MessageReadSerializer
    object_model = Message
    permission_classes = (IsAuthenticated, MessageAccessPermissions)


class MessageDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Message.

    Example:

        GET /api/v1/messages/xxxxxxxxxxxxx/
    """
    serializer_class = MessageReadSerializer
    queryset = Message
    permission_classes = (IsAuthenticated, MessageAccessPermissions)


class BroadcastList(DataListAPIView):
    """
    This endpoint allows you to list Broadcasts.

    ## Filters

    You can use the filters below in the url query string(```?filter=value```) to filter the data

    * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)

    ## Listing Broadcasts
    """
    serializer_class = BroadcastReadSerializer
    object_model = Broadcast


class BroadcastDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Broadcast.

    Example:

        GET /api/v1/broadcasts/xxxxxxxxxxxxx/
    """
    serializer_class = BroadcastReadSerializer
    queryset = Broadcast


class CampaignList(DataListAPIView):
    """
    This endpoint allows you to list Campaigns.

    ## Filters

    You can use the filters below in the url query string(```?filter=value```) to filter the data

    * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int))

    ## Listing Campaigns
    """
    serializer_class = CampaignReadSerializer
    object_model = Campaign


class CampaignDetails(RetrieveAPIView):
    """
    This endpoint allows you to a single Campaign.

    Example:

        GET /api/v1/campaigns/xxxxxxxxxxxxx/
    """
    serializer_class = CampaignReadSerializer
    queryset = Campaign


# class EventList(DataListAPIView):
#     """
#     This endpoint allows you to list Events.
#
#     ## Filters
#
#     You can use the filters below in the url query string(```?filter=value```) to filter the data
#
#     * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)
#
#     ## Listing Events
#     """
#     serializer_class = EventReadSerializer
#     object_model = Event
#
#
# class EventDetails(RetrieveAPIView):
#     """
#     This endpoint allows you to a single Event.
#
#     ## Filters
#
#     You can use the filters below in the url query string(```?filter=value```) to filter the data
#
#     * **page_size** - Determine number of results per page. Maximum 1000, default 10 (int)
#
#     Example:
#
#         GET /api/v1/events/xxxxxxxxxxxxx/
#     """
#     serializer_class = EventReadSerializer
#     queryset = Event
