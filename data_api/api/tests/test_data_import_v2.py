import codecs
import json
import os
from unittest import skip
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from mock import patch
from rest_framework.test import APIRequestFactory, APIClient
import six
from temba_client.tests import TembaTest, MockResponse
from temba_client.v2 import TembaClient
import uuid
from ..models import Org, Boundary, Broadcast, Contact, Group, Channel, ChannelEvent, Campaign, CampaignEvent, \
    Field, Flow, Label, FlowStart, Run, Resthook, ResthookEvent, ResthookSubscriber, Message
from data_api.api.tasks import fetch_entity


@patch('temba_client.clients.request')
class V2TembaTest(TembaTest):
    # this class heavily inspired by temba_client.v2.tests.TembaClientTest

    def read_json(self, filename, extract_result=None):
        """
        Loads JSON from the given test file
        """
        handle = codecs.open(os.path.join(os.path.dirname(__file__), 'test_api_results',
                                          '{}.json'.format(filename)))
        contents = six.text_type(handle.read())
        handle.close()

        if extract_result is not None:
            contents = json.dumps(json.loads(contents)['results'][0])

        return contents

    @classmethod
    def setUpClass(cls):
        cls.api_token = uuid.uuid4().hex
        cls.client = TembaClient('example.com', '1234567890', user_agent='test/0.1')
        cls.org = Org.create(name='test org', api_token=cls.api_token, timezone=None)

        # for API tests
        username = 'unicef'
        password = '4thekids'
        cls.user = User.objects.create_user(
            username=username, email='rapidpro@unicef.org', password=password, is_superuser=True)
        cls.client = APIClient()
        cls.client.login(username=username, password=password)

    def tearDown(self):
        Broadcast.objects.all().delete()
        Campaign.objects.all().delete()
        CampaignEvent.objects.all().delete()
        Channel.objects.all().delete()
        ChannelEvent.objects.all().delete()
        Contact.objects.all().delete()
        Group.objects.all().delete()
        Flow.objects.all().delete()
        FlowStart.objects.all().delete()
        Label.objects.all().delete()
        Message.objects.all().delete()
        Run.objects.all().delete()
        Resthook.objects.all().delete()
        ResthookEvent.objects.all().delete()
        ResthookSubscriber.objects.all().delete()

    def _run_import_test(self, mock_request, obj_class):
        api_results_text = self.read_json(obj_class._meta['collection'])
        api_results = json.loads(api_results_text)
        mock_request.return_value = MockResponse(200, api_results_text)
        before = datetime.utcnow()
        objs_made = fetch_entity(obj_class, self.org)
        after = datetime.utcnow()
        for obj in objs_made:
            self.assertTrue(isinstance(obj, obj_class))
            self.assertEqual(str(self.org.id), obj.org_id)
            self.assertTrue(before <= obj.first_synced <= after)
            self.assertTrue(before <= obj.last_synced <= after)

        return api_results['results'], objs_made

    def _run_api_test(self, obj_class):
        # assumes run after an import has been done
        collection_name = obj_class._meta['collection']
        rapidpro_api_results = json.loads(self.read_json(collection_name))['results']
        # todo: should ideally not hard-code urls like this
        warehouse_api_results = self.client.get('/api/v2/{}/org/{}/'.format(collection_name,
                                                                            str(self.org.id))).json()
        self.assertEqual(
            len(rapidpro_api_results),
            len(warehouse_api_results),
            'API result lenghts were different: \nRapidPRO\n{}\nWarehouse\n{}'.format(
                json.dumps(rapidpro_api_results, indent=2),
                json.dumps(warehouse_api_results, indent=2)
            )
        )
        for i, rapidpro_result in enumerate(rapidpro_api_results):
            self.assertApiObjectsEquivalent(rapidpro_result, warehouse_api_results[i])

    def assertApiObjectsEquivalent(self, rapidpro_result, warehouse_api_result):
        IGNORE_KEYS = {'id'}
        IGNORE_TYPES = (list, dict)  # todo: probably want to test these eventually
        for key in rapidpro_result:
            rapidpro_value = rapidpro_result[key]
            if key in IGNORE_KEYS:
                continue
            if not isinstance(rapidpro_value, IGNORE_TYPES):
                warehouse_value = warehouse_api_result[key]
                self.assertEqual(
                    _massage_data(rapidpro_value),
                    _massage_data(warehouse_value),
                    '{} was not the same (expected {}, got {})'.format(
                        key, rapidpro_value, warehouse_value
                    )
                )

    def test_import_boundaries(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Boundary)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])
        self._run_api_test(Boundary)

    def test_import_broadcasts(self, mock_request):
        Contact(org_id=str(self.org.id), uuid='5079cb96-a1d8-4f47-8c87-d8c7bb6ddab9').save()
        Group(org_id=str(self.org.id), uuid='04a4752b-0f49-480e-ae60-3a3f2bea485c').save()
        api_results, objs_made = self._run_import_test(mock_request, Broadcast)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.text, api_results[i]['text'])
        self._run_api_test(Broadcast)

    def test_import_campaigns(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Campaign)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])
        self._run_api_test(Campaign)

    def test_import_campaign_events(self, mock_request):
        Campaign(org_id=str(self.org.id), uuid='9ccae91f-b3f8-4c18-ad92-e795a2332c11').save()
        api_results, objs_made = self._run_import_test(mock_request, CampaignEvent)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.message, api_results[i]['message'])

    def test_import_channels(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Channel)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_channel_events(self, mock_request):
        Channel(org_id=str(self.org.id), uuid='9a8b001e-a913-486c-80f4-1356e23f582e').save()
        Contact(org_id=str(self.org.id), uuid='d33e9ad5-5c35-414c-abd4-e7451c69ff1d').save()
        api_results, objs_made = self._run_import_test(mock_request, ChannelEvent)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.tid, api_results[i]['id'])

    def test_import_contacts(self, mock_request):
        # todo: find a more generic way to bootstrap related models
        Group(org_id=str(self.org.id), uuid='d29eca7c-a475-4d8d-98ca-bff968341356').save()
        api_results, objs_made = self._run_import_test(mock_request, Contact)
        self.assertEqual(3, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])
        self._run_api_test(Contact)

    def test_import_fields(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Field)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.key, api_results[i]['key'])

    @skip('import currently succeeds on bad object references because errors are swallowed')
    def test_import_fails_if_no_related_object(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, FlowStart)
        self.assertEqual(0, len(objs_made))

    def test_import_flow_starts(self, mock_request):
        Flow(org_id=str(self.org.id), uuid='f5901b62-ba76-4003-9c62-72fdacc1b7b7', name='Registration').save()
        Flow(org_id=str(self.org.id), uuid='f5901b62-ba76-4003-9c62-72fdacc1b7b8', name='Thrift Shop').save()
        api_results, objs_made = self._run_import_test(mock_request, FlowStart)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.flow.name, api_results[i]['flow']['name'])

    def test_import_flows(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Flow)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_groups(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Group)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_labels(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Label)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_messages(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Message)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.text, api_results[i]['text'])

    def test_import_org(self, mock_request):
        api_results_text = self.read_json('org')
        api_results = json.loads(api_results_text)
        mock_request.return_value = MockResponse(200, api_results_text)
        api_key = 'token'
        client = TembaClient('host', api_key)
        org = Org.import_from_temba(client, api_key)
        self.assertEqual(api_key, org.api_token)
        self.assertEqual(org.name, api_results['name'])

    def test_import_runs(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Run)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.tid, api_results[i]['id'])

    def test_import_resthooks(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, Resthook)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.resthook, api_results[i]['resthook'])

    def test_import_resthook_events(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, ResthookEvent)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.resthook, api_results[i]['resthook'])

    def test_import_resthook_subscribers(self, mock_request):
        api_results, objs_made = self._run_import_test(mock_request, ResthookSubscriber)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.resthook, api_results[i]['resthook'])


def _massage_data(value):
    if _looks_like_a_date_string(value):
        # mongo strips microseconds so we have to as well.
        # todo: This could be drastically improved.
        return value[:23]

    return value


def _looks_like_a_date_string(value):
    # todo: can make this more advanced as needed
    return isinstance(value, basestring) and value.endswith('Z') and len(value) == 27
