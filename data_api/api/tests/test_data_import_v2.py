import codecs
import json
import os
from unittest import skip
from mock import patch
import six
from temba_client.tests import TembaTest, MockResponse
from temba_client.v2 import TembaClient
import uuid
from ..models import Org, Boundary, Broadcast, Contact, Group, Channel
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

    @classmethod
    def tearDownClass(cls):
        Broadcast.objects.all().delete()
        Group.objects.all().delete()
        Contact.objects.all().delete()

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

    @skip("Related objects are not working yet")
    def test_import_broadcasts(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Broadcast)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.text, api_results[i]['text'])

    def test_import_channels(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Channel)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_contacts(self, mock_request):
        # todo: find a more generic way to bootstrap related models
        Group(org_id=str(self.org.id), uuid='d29eca7c-a475-4d8d-98ca-bff968341356').save()
        api_results, objs_made = self._run_test(mock_request, Contact)
        self.assertEqual(3, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])

    def test_import_groups(self, mock_request):
        api_results, objs_made = self._run_test(mock_request, Group)
        self.assertEqual(2, len(objs_made))
        for i, obj in enumerate(objs_made):
            self.assertEqual(obj.name, api_results[i]['name'])
