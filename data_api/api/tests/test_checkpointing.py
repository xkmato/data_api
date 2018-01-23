from datetime import datetime
from django.test import SimpleTestCase, TestCase
from temba_client.v2 import TembaClient
import uuid
from data_api.api.models import get_fetch_kwargs, LastSaved, Org, Message


class LastSavedTest(TestCase):
    def setUp(self):
        self.org = Org.create(name='test org', api_token=uuid.uuid4().hex, timezone=None)

    def tearDown(self):
        self.org.delete()

    def test_get_none(self):
        ls = LastSaved.get_for_org_and_collection(self.org, Message)
        self.assertEqual(None, ls)

    def test_create_and_get(self):
        ls = LastSaved.create_for_org_and_collection(self.org, Message)
        ls.save()
        ls_back = LastSaved.get_for_org_and_collection(self.org, Message)
        self.assertEqual(ls, ls_back)


class FetchArgsTest(SimpleTestCase):

    def _method_with_after_arg(self, before=None, after=None):
        pass

    def _method_without_after_arg(self, uuid=None, campaign=None):
        pass

    def _method_without_args(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(FetchArgsTest, cls).setUpClass()
        cls.last_saved_good = LastSaved(last_saved=datetime.utcnow())
        cls.last_saved_bad = LastSaved(last_saved=None)

    def test_method_with_after_arg(self):
        self.assertEqual({'after': self.last_saved_good.last_saved},
                         get_fetch_kwargs(self._method_with_after_arg, self.last_saved_good))

    def test_methods_without_after_args(self):
        self.assertEqual({}, get_fetch_kwargs(self._method_without_after_arg, self.last_saved_good))
        self.assertEqual({}, get_fetch_kwargs(self._method_without_args, self.last_saved_good))

    def test_last_saved_none(self):
        self.assertEqual({}, get_fetch_kwargs(self._method_with_after_arg, None))

    def test_last_saved_bad(self):
        self.assertEqual({}, get_fetch_kwargs(self._method_with_after_arg, self.last_saved_bad))

    def test_rapidpro_apis(self):
        client = TembaClient('example.com', 's3cret')
        self.assertEqual({}, get_fetch_kwargs(client.get_boundaries, self.last_saved_good))
        self.assertEqual({'after': self.last_saved_good.last_saved},
                         get_fetch_kwargs(client.get_broadcasts, self.last_saved_good))
