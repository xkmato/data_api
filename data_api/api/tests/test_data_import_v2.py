import codecs
import json
import os
from mock import patch
import six
from temba_client.tests import TembaTest, MockResponse
from temba_client.v2 import TembaClient
from ..models import Org, Boundary
from data_api.api.tasks import fetch_entity


@patch('temba_client.clients.request')
class V2TembaTest(TembaTest):
    # this class heavily inspired by temba_client.v2.tests.TembaClientTest

    def read_json(self, filename, extract_result=None):
        """
        Loads JSON from the given test file
        """
        handle = codecs.open(os.path.join(os.path.dirname(__file__), 'test_api_results', '{}.json'.format(filename)))
        contents = six.text_type(handle.read())
        handle.close()

        if extract_result is not None:
            contents = json.dumps(json.loads(contents)['results'][0])

        return contents

    @classmethod
    def setUpClass(cls):
        cls.client = TembaClient('example.com', '1234567890', user_agent='test/0.1')
        cls.org = Org.create(name='test org', api_token='f00b4r', timezone=None)

    def test_get_boundaries(self, mock_request):
        mock_request.return_value = MockResponse(200, self.read_json('boundaries'))
        fetch_entity(Boundary, self.org)
