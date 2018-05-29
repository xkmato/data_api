import logging
import traceback
from datetime import datetime
from django.conf import settings
from django.core.mail import mail_admins
from retrying import retry
from temba_client.exceptions import TembaConnectionError, TembaBadRequestError, TembaTokenError, \
    TembaRateExceededError, TembaException
from celery import task

from data_api.api.exceptions import ImportRunningException

__author__ = 'kenneth'

logging.basicConfig(format=settings.LOG_FORMAT)
logger = logging.getLogger("tasks")


def retry_if_temba_api_or_connection_error(exception):
    if isinstance(exception, (TembaBadRequestError, TembaTokenError)):
        return False
    if isinstance(exception, (TembaConnectionError, TembaRateExceededError)):
        logger.warning("Raised an exception: %s - Retrying in %s minutes", str(exception),
                       str(settings.RETRY_WAIT_FIXED/60000))
        return True
    return False


@retry(retry_on_exception=retry_if_temba_api_or_connection_error, stop_max_attempt_number=settings.RETRY_MAX_ATTEMPTS,
       wait_fixed=settings.RETRY_WAIT_FIXED)
def fetch_entity(entity, org, return_objs=False):
    logger.info("Fetching objects of type: %s for Org: %s", str(entity), org.name)
    return entity.sync_all_data(org, return_objs)


def get_org_entities(sql):
    from data_api.api.models import OrgDocument
    from data_api.staging.models import OrganizationModel
    if not sql:
        return OrgDocument.__subclasses__()
    else:
        return OrganizationModel.__subclasses__()


def get_all_orgs(sql):
    from data_api.api.models import Org
    from data_api.staging.models import Organization
    if not sql:
        return Org.objects.filter(is_active=True)
    else:
        return Organization.objects.filter(is_active=True)


def get_orgs_by_api_keys(api_keys, sql):
    from data_api.api.models import Org
    from data_api.staging.models import Organization
    if not sql:
        [Org.objects.get(**{'api_token': api_key}) for api_key in api_keys]
    else:
        return Organization.objects.filter(api_token__in=api_keys)


@task
def sync_latest_data(entities=None, orgs=None, sql=False):
    """
    Syncs the latest data from configured rapidpro Orgs.

    The default value for both arguments is to sync _all_ entities/orgs.
    """
    mail_admins('Starting RapidPro data sync', '')
    start_time = datetime.now()
    if not entities:
        entities = get_org_entities(sql)
    if not orgs:
        orgs = get_all_orgs(sql)
    else:
        orgs = get_orgs_by_api_keys(orgs, sql)
    assert iter(entities)
    for org in orgs:
        for entity in entities:
            try:
                fetch_entity(entity, org)
            except ImportRunningException as e:
                logger.error(str(e))
                continue
            except TembaException as e:
                if settings.DEBUG:
                    raise
                logger.error("Temba is misbehaving: %s - No retry", str(e))
                continue
            except Exception as e:
                if settings.DEBUG:
                    raise
                logger.error("Things are dead: %s - No retry", str(traceback.format_exc()))

    task_duration = datetime.now() - start_time
    mail_admins('Finished RapidPro data sync in {} seconds'.format(task_duration.seconds), '')


@task
def generate_message_dumps(from_date=None, org=None, contact_fields=None):
    from data_api.api.models import Message
    Message.generate_csv(from_date=from_date, org_id=org, contact_fields=contact_fields)

@task
def generate_run_dumps(from_date=None, org=None, contact_fields=None):
    from data_api.api.models import Run
    Run.generate_csv(from_date=from_date, org_id=org, contact_fields=contact_fields)
