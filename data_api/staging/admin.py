from django.contrib import admin

from data_api.staging import models


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'is_active', 'server', 'api_token']
    list_filter = ['is_active', 'server']


ORG_MODEL_FIELDS = ['organization', 'first_synced', 'last_synced']


class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'uuid'] + ORG_MODEL_FIELDS
    list_filter = ORG_MODEL_FIELDS


class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'uuid'] + ORG_MODEL_FIELDS
    list_filter = ORG_MODEL_FIELDS


admin.site.register(models.Organization, OrganizationAdmin)
admin.site.register(models.Group, GroupAdmin)
admin.site.register(models.Contact, ContactAdmin)
admin.site.register(models.Field)
admin.site.register(models.Channel)
admin.site.register(models.ChannelEvent)
