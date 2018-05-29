import inspect
from abc import ABCMeta, abstractmethod
from datetime import datetime

import pytz

from data_api.api.exceptions import ImportRunningException


class IngestionCheckpoint(object):
    __metaclass__ = ABCMeta

    def __init__(self, org, collection_class, checkpoint_time):
        self.org = org
        self.collection_class = collection_class
        self.checkpoint_time = checkpoint_time

    @classmethod
    def get_checkpoint(self, org, collection_class, checkpoint_time):
        from data_api.api.models import Org
        from data_api.staging.models import Organization
        if isinstance(org, Org):
            return MongoIngestionCheckpoint(org, collection_class, checkpoint_time)
        else:
            assert isinstance(org, Organization)
            return SqlIngestionCheckpoint(org, collection_class, checkpoint_time)

    @abstractmethod
    def exists(self):
        pass

    @abstractmethod
    def is_running(self):
        pass

    @abstractmethod
    def get_last_checkpoint_time(self):
        pass

    @abstractmethod
    def create_and_start(self):
        pass

    @abstractmethod
    def set_finished(self):
        pass


class MongoIngestionCheckpoint(IngestionCheckpoint):

    def __init__(self, org, collection_class, checkpoint_time):
        from data_api.api.models import LastSaved
        super(MongoIngestionCheckpoint, self).__init__(org, collection_class, checkpoint_time)
        self._last_saved = LastSaved.get_for_org_and_collection(org, collection_class)
        self._exists = self._last_saved is not None

    def exists(self):
        return self._exists

    def is_running(self):
        return self.exists() and self._last_saved.is_running

    def get_last_checkpoint_time(self):
        if not self.exists():
            return None
        return self._last_saved.last_saved

    def create_and_start(self):
        from data_api.api.models import LastSaved
        ls = LastSaved.create_for_org_and_collection(self.org, self.collection_class)
        ls.last_started = self.checkpoint_time
        ls.is_running = True
        ls.save()
        self._last_saved = ls

    def set_finished(self):
        self._last_saved.last_saved = self.checkpoint_time
        self._last_saved.is_running = False
        self._last_saved.save()


class SqlIngestionCheckpoint(IngestionCheckpoint):

    def __init__(self, org, collection_class, checkpoint_time):
        from data_api.staging.models import SyncCheckpoint
        super(SqlIngestionCheckpoint, self).__init__(org, collection_class, checkpoint_time)
        try:
            self._checkpoint = SyncCheckpoint.objects.get(
                organization=org, collection_name=collection_class.get_collection_name()
            )
            self._exists = True
        except SyncCheckpoint.DoesNotExist:
            self._checkpoint = None
            self._exists = False

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
        return cls.create_from_temba_list(org, fetch_method(**fetch_kwargs), return_objs,
                                          is_initial_import=initial_import)

    @classmethod
    def get_fetch_method(cls, org):
        func = "get_%s" % cls.get_collection_name()
        return getattr(org.get_temba_client(), func)

    @classmethod
    def create_from_temba_list(cls, org, temba_list, return_objs=False, is_initial_import=False):
        obj_list = []
        chunk_to_save = []
        chunk_size = 100

        def _object_found(temba_obj):
            q = None
            if hasattr(temba_obj, 'uuid'):
                q = {'uuid': temba_obj.uuid}
            elif hasattr(temba_obj, 'id'):
                q = {'tid': temba_obj.id}
            return q and cls.objects.filter(**q).first()

        for temba in temba_list.all(retry_on_rate_exceed=True):
            # only bother importing the object if either it's the first time we're importing data
            # for this org/type or if we didn't find existing data in the DB already
            if is_initial_import or not _object_found(temba):
                obj = cls.create_from_temba(org, temba, do_save=False)
                chunk_to_save.append(obj)
                if return_objs:
                    obj_list.append(obj)
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
