import codecs
import json
import os
from unittest import skip
from mock import patch
import six
from temba_client.tests import TembaTest, MockResponse
from temba_client.v2 import TembaClient
import uuid
from ..models import Org, Boundary, Broadcast, Contact, Group, Channel, ChannelEvent, Campaign, CampaignEvent, \
    Field
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

    def tearDown(self):
        Broadcast.objects.all().delete()
        Campaign.objects.all().delete()
        CampaignEvent.objects.all().delete()
        Channel.objects.all().delete()
        ChannelEvent.objects.all().delete()
        Contact.objects.all().delete()
        Group.objects.all().delete()

    def _run_test(self, mock_request, obj_class):
        api_results_text = self.read_json(obj_class._meta['collection'])
        api_results = json.loads(api_results_text)
        mock_request.return_value = MockResponse(200, api_results_text)
        objs_made = fetch_entity(obj_class, self.org)
        for obj in objs_made:
            self.assertTrue(isinstance(obj, obj_class))

        return api_results['results'], objs_made

    def test_import_boundaries(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Boundary)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_broadcasts(self, mock_request):
        Contact(org_id=str(self.org.id), uuid='5079cb96-a1d8-4f47-8c87-d8c7bb6ddab9').save()
        Group(org_id=str(self.org.id), uuid='04a4752b-0f49-480e-ae60-3a3f2bea485c').save()
        api_results, objs_made = self._run_test(mock_request, Broadcast)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.text, api_results[i]['text'])

    def test_import_campaigns(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Campaign)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_campaign_events(self, mock_request):
        Campaign(org_id=str(self.org.id), uuid='9ccae91f-b3f8-4c18-ad92-e795a2332c11').save()
        api_results, objs_made = self._run_test(mock_request, CampaignEvent)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.message, api_results[i]['message'])

    def test_import_channels(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Channel)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_channel_events(self, mock_request):
        Channel(org_id=str(self.org.id), uuid='9a8b001e-a913-486c-80f4-1356e23f582e').save()
        Contact(org_id=str(self.org.id), uuid='d33e9ad5-5c35-414c-abd4-e7451c69ff1d').save()
        api_results, objs_made = self._run_test(mock_request, ChannelEvent)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.tid, api_results[i]['id'])

    def test_import_contacts(self, mock_request):
        # todo: find a more generic way to bootstrap related models
        Group(org_id=str(self.org.id), uuid='d29eca7c-a475-4d8d-98ca-bff968341356').save()
        api_results, objs_made = self._run_test(mock_request, Contact)
        self.assertEqual(3, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_fields(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Field)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.key, api_results[i]['key'])

    def test_import_groups(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Group)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])
