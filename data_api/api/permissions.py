from django.conf import settings
from django.contrib.auth.models import Group
from rest_framework import permissions

__author__ = 'kenneth'


class ContactAccessPermissions(permissions.BasePermission):
    message = 'Please request for permission to access this resource'

    def has_permission(self, request, view):
        g = Group.objects.filter(name=getattr(settings, 'CONTACT_ACCESS_GROUP', "contact_access")).first()
        return request.user.is_superuser or (g is not None and g in request.user.groups.all())
