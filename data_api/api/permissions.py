from django.conf import settings
from django.contrib.auth.models import Group
from rest_framework import permissions

__author__ = 'kenneth'


class EntityAccessPermissions(permissions.BasePermission):
    message = 'Please request for permission to access this resource'

    def has_permission(self, request, view):
        g = Group.objects.filter(name=self._group).first()
        return request.user.is_superuser or (g is not None and g in request.user.groups.all())


class ContactAccessPermissions(EntityAccessPermissions):
    _group = getattr(settings, 'CONTACT_ACCESS_GROUP', "contact_access")


class MessageAccessPermissions(EntityAccessPermissions):
    _group = getattr(settings, 'MESSAGE_ACCESS_GROUP', "message_access")


class OrgAccessPermissions(EntityAccessPermissions):
    _group = getattr(settings, 'ORG_ACCESS_GROUP', "org_access")