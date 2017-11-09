from django.http import Http404
from mongoengine import QuerySet, ValidationError


# NOTE: this file was copy/pasted from an older version of mongoengine that had some django support
# https://github.com/newvem/mongoengine/blob/master/mongoengine/django/shortcuts.py

def _get_queryset(cls):
    """Inspired by django.shortcuts.*"""
    if isinstance(cls, QuerySet):
        return cls
    else:
        return cls.objects


def get_document_or_404(cls, *args, **kwargs):
    """
    Uses get() to return an document, or raises a Http404 exception if the document
    does not exist.
    cls may be a Document or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.
    Note: Like with get(), an MultipleObjectsReturned will be raised if more than one
    object is found.
    Inspired by django.shortcuts.*
    """
    queryset = _get_queryset(cls)
    try:
        return queryset.get(*args, **kwargs)
    except (queryset._document.DoesNotExist, ValidationError):
        raise Http404('No %s matches the given query.' % queryset._document._class_name)
