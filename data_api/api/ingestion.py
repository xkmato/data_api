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
        from data_api.rapidpro_staging.models import Organization
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
    # todo implement this class
    def exists(self):
        pass

    def is_running(self):
        pass

    def get_last_checkpoint_time(self):
        pass

    def create_and_start(self):
        pass

    def set_finished(self):
        pass


class RapidproAPIBaseModel(object):

    @classmethod
    def get_collection_name(self):
        # abstract method
        raise NotImplementedError()

    @classmethod
    def object_count(cls, org):
        # abstract method
        raise NotImplementedError()

    @classmethod
    def fetch_objects(cls, org, return_objs=False):
        """
        Syncs all objects of this type from the provided org.
        """
        checkpoint_time = datetime.utcnow()
        checkpoint = IngestionCheckpoint.get_checkpoint(org, cls, checkpoint_time)
        if not checkpoint.exists():
            checkpoint.create_and_start()
        elif checkpoint.is_running():
            raise ImportRunningException('Import for model {} in org {} still pending!'.format(
                cls.__name__, org.name,
            ))
        objs = cls.sync_temba_objects(org, checkpoint, return_objs)
        checkpoint.set_finished()
        return objs

    @classmethod
    def sync_temba_objects(cls, org, checkpoint, return_objs=False):
        fetch_method = cls.get_fetch_method(org)
        fetch_kwargs = get_fetch_kwargs(fetch_method, checkpoint)
        initial_import = cls.object_count(org) == 0
        return cls.create_from_temba_list(org, fetch_method(**fetch_kwargs), return_objs,
                                          is_initial_import=initial_import)

    @classmethod
    def get_fetch_method(cls, org):
        func = "get_%s" % cls.get_collection_name()
        return getattr(org.get_temba_client(), func)


def get_fetch_kwargs(fetch_method, checkpoint):
    if checkpoint and checkpoint.exists() and checkpoint.get_last_checkpoint_time():
        method_args = inspect.getargspec(fetch_method)[0]
        if 'after' in method_args:
            return {
                'after': pytz.utc.localize(checkpoint.get_last_checkpoint_time())
            }
    return {}
