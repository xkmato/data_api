import gzip
import inspect
import json
from datetime import datetime
from tempfile import NamedTemporaryFile

import pytz
import requests
from sentry_sdk import capture_exception, configure_scope

from data_api.staging.exceptions import ImportRunningException


class IngestionCheckpoint(object):

    def __init__(self, org, collection_class, checkpoint_time, subcollection=None):
        from data_api.staging.models import SyncCheckpoint
        self.org = org
        self.collection_class = collection_class
        self.checkpoint_time = checkpoint_time
        self.subcollection = subcollection
        try:
            self._checkpoint = SyncCheckpoint.objects.get(
                organization=org,
                collection_name=collection_class.get_collection_name(),
                subcollection_name=self.subcollection,
            )
            self._exists = True
        except SyncCheckpoint.DoesNotExist:
            self._checkpoint = None
            self._exists = False

    @classmethod
    def get_checkpoint(self, org, collection_class, checkpoint_time):
        from data_api.staging.models import Organization
        assert isinstance(org, Organization)
        return IngestionCheckpoint(org, collection_class, checkpoint_time)

    def exists(self):
        return self._exists

    def is_running(self):
        return self.exists() and self._checkpoint.is_running

    def get_last_checkpoint_time(self):
        if not self.exists():
            return None
        return self._checkpoint.last_saved

    def create_and_start(self):
        from data_api.staging.models import SyncCheckpoint
        self._checkpoint = SyncCheckpoint.objects.create(
            organization=self.org,
            collection_name=self.collection_class.get_collection_name(),
            subcollection_name=self.subcollection,
            last_started=self.checkpoint_time,
            is_running=True,
        )

    def set_finished(self):
        self._checkpoint.last_saved = self.checkpoint_time
        self._checkpoint.is_running = False
        self._checkpoint.save()


class RapidproAPIBaseModel(object):

    # ============ abstract methods ============
    # due to issues with django/mongoengine relying on metaclasses, we can't easily use ABCMeta for these
    # more info here: https://stackoverflow.com/q/8723639/8207
    @classmethod
    def get_collection_name(self):
        raise NotImplementedError()

    @classmethod
    def object_count(cls, org):
        raise NotImplementedError()

    @classmethod
    def create_from_temba(cls, org, temba, do_save):
        raise NotImplementedError()

    @classmethod
    def bulk_save(cls, chunk_to_save):
        raise NotImplementedError()

    # ============ real methods ============
    @classmethod
    def sync_all_data(cls, org, return_objs=False):
        """
        Syncs all objects of this type from the provided org.
        """
        checkpoint_time = datetime.now(tz=pytz.utc)
        checkpoint = IngestionCheckpoint.get_checkpoint(org, cls, checkpoint_time)
        if not checkpoint.exists():
            checkpoint.create_and_start()
        elif checkpoint.is_running():
            raise ImportRunningException('Import for model {} in org {} still pending!'.format(
                cls.__name__, org.name,
            ))
        objs = cls.sync_data_with_checkpoint(org, checkpoint, return_objs)
        checkpoint.set_finished()
        return objs

    @classmethod
    def sync_data_with_checkpoint(cls, org, checkpoint, return_objs=False):
        fetch_method = cls.get_fetch_method(org)
        fetch_kwargs = get_fetch_kwargs(fetch_method, checkpoint)
        initial_import = cls.object_count(org) == 0
        temba_generator = fetch_method(**fetch_kwargs).all(retry_on_rate_exceed=True)
        return cls.create_from_temba_list(org, temba_generator, return_objs,
                                          is_initial_import=initial_import)

    @classmethod
    def get_fetch_method(cls, org):
        func = "get_%s" % cls.get_collection_name()
        return getattr(org.get_temba_client(), func)

    @classmethod
    def create_from_temba_list(cls, org, temba_generator, return_objs=False, is_initial_import=False):
        obj_list = []
        chunk_to_save = []
        chunk_size = 100

        def _object_found(temba_obj):
            q = None
            if hasattr(temba_obj, 'uuid'):
                q = {'uuid': temba_obj.uuid}
            elif hasattr(temba_obj, 'id'):
                q = {'rapidpro_id': temba_obj.id}
            return q and cls.objects.filter(**q).first()

        for temba in temba_generator:
            # only bother importing the object if either it's the first time we're importing data
            # for this org/type or if we didn't find existing data in the DB already
            try:
                if is_initial_import or not _object_found(temba):
                    obj = cls.create_from_temba(org, temba, do_save=False)
                    chunk_to_save.append(obj)
                    if return_objs:
                        obj_list.append(obj)
            except Exception as e:
                with configure_scope() as scope:
                    scope.set_extra('temba_dict', temba.serialize())
                    capture_exception(e)
                    raise
            if len(chunk_to_save) > chunk_size:
                cls.bulk_save(chunk_to_save)
                chunk_to_save = []

        if chunk_to_save:
            cls.bulk_save(chunk_to_save)

        return obj_list


def get_fetch_kwargs(fetch_method, checkpoint):
    if checkpoint and checkpoint.exists() and checkpoint.get_last_checkpoint_time():
        method_args = inspect.getargspec(fetch_method)[0]
        if 'after' in method_args:
            checkpoint_time = checkpoint.get_last_checkpoint_time()
            # add timezone info if not present
            if checkpoint_time.tzinfo is None or checkpoint_time.tzinfo.utcoffset(checkpoint_time) is None:
                checkpoint_time = pytz.utc.localize(checkpoint_time)
            return {
                'after': checkpoint_time
            }
    return {}


def ensure_timezone(checkpoint_time):
    if checkpoint_time.tzinfo is None or checkpoint_time.tzinfo.utcoffset(checkpoint_time) is None:
        checkpoint_time = pytz.utc.localize(checkpoint_time)
    return checkpoint_time


def download_archive_to_temporary_file(download_url):
    f = NamedTemporaryFile(delete=False)
    r = requests.get(download_url, stream=True)
    with open(f.name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return f.name


def iter_archive(filename):
    """
    Iterates through an archive file and yields the results as json
    :param temp_file_name:
    :return: an iterator of json wrapped objects
    """
    with gzip.open(filename, 'rt') as f:
        for line in f.readlines():
            yield json.loads(line)
