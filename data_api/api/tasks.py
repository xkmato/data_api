import logging
import traceback
from django.conf import settings
import requests
from retrying import retry
from temba.base import TembaAPIError, TembaConnectionError, TembaException, TembaPager
from data_api.api.models import BaseUtil, Org, Message, Run
from djcelery_transactions import task

__author__ = 'kenneth'

logging.basicConfig(format=settings.LOG_FORMAT)
logger = logging.getLogger("tasks")


def retry_if_temba_api_or_connection_error(exception):
    if isinstance(exception, TembaAPIError) and isinstance(exception.caused_by,
                                                           requests.HTTPError
                                                           ) and 399 < exception.caused_by.response.status_code < 500:
        return False
    if isinstance(exception, TembaAPIError) or isinstance(exception, TembaConnectionError):
        logger.warning("Raised an exception: %s - Retrying in %s minutes", str(exception),
                   str(settings.RETRY_WAIT_FIXED/60000))
        return True
    return False


@retry(retry_on_exception=retry_if_temba_api_or_connection_error, stop_max_attempt_number=settings.RETRY_MAX_ATTEMPTS,
       wait_fixed=settings.RETRY_WAIT_FIXED)
def fetch_entity(entity, org, n):
    entity = entity.get('name')
    logger.info("Fetching Object of type: %s for Org: %s on Page %s", str(entity), org.name, str(n))
    entity.fetch_objects(org, pager=TembaPager(n))


@task
def fetch_all(entities=None, orgs=None):
    print "Started Here"
    if not entities:
        entities = [dict(name=cls) for cls in BaseUtil.__subclasses__()]
    if not orgs:
        orgs = Org.objects.all({"is_active": True})
    else:
        orgs = [Org.objects.get(**{'api_token': api_key}) for api_key in orgs]
    assert iter(entities)
    for org in orgs:
        for entity in entities:
            try:
                n = entity.get('start_page', 1)
                while True:
                    fetch_entity(entity, org, n)
                    n += 1
            except TembaException as e:
                logger.error("Temba is misbehaving: %s - No retry", str(e))
                continue
            except Exception as e:
                logger.error("Things are dead: %s - No retry", str(traceback.format_exc()))


@task
def generate_message_dumps():
    Message.generate_csv()

@task
def generate_run_dumps():
    Run.generate_csv()
