from datetime import datetime

import pytz
from django.test import SimpleTestCase, TestCase
from temba_client.v2 import TembaClient
import uuid
from data_api.api.models import get_fetch_kwargs, LastSaved, Org, Message, Group


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

    def test_get_for_wrong_org(self):
        ls = LastSaved.create_for_org_and_collection(self.org, Message)
        ls.save()
        org2 = Org.create(name='test org 2', api_token=uuid.uuid4().hex, timezone=None)
        self.assertEqual(None, LastSaved.get_for_org_and_collection(org2, Message))

    def test_get_for_wrong_collection(self):
        ls = LastSaved.create_for_org_and_collection(self.org, Message)
        ls.save()
        self.assertEqual(None, LastSaved.get_for_org_and_collection(self.org, Group))


class LastSavedMessagesTest(TestCase):
    def setUp(self):
        self.org = Org.create(name='test org', api_token=uuid.uuid4().hex, timezone=None)

    def tearDown(self):
        self.org.delete()

    def test_get_none(self):
        ls = Message.get_last_saved_for_folder(self.org, 'inbox')
        self.assertEqual(None, ls)

    def test_folder_uniqueness(self):
        ls = Message.create_last_saved_for_folder(self.org, 'inbox')
        ls.save()
        ls_back = Message.get_last_saved_for_folder(self.org, 'sent')
        self.assertEqual(None, ls_back)

    def test_get_for_wrong_org(self):
        ls = Message.create_last_saved_for_folder(self.org, 'inbox')
        ls.save()
        org2 = Org.create(name='test org 2', api_token=uuid.uuid4().hex, timezone=None)
        self.assertEqual(None, Message.get_last_saved_for_folder(org2, 'inbox'))

    def test_get_for_wrong_folder(self):
        ls = Message.create_last_saved_for_folder(self.org, 'inbox')
        ls.save()
        self.assertEqual(None, Message.get_last_saved_for_folder(self.org, 'sent'))


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
        self.assertEqual({'after': pytz.utc.localize(self.last_saved_good.last_saved)},
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
        self.assertEqual({'after': pytz.utc.localize(self.last_saved_good.last_saved)},
                         get_fetch_kwargs(client.get_broadcasts, self.last_saved_good))
