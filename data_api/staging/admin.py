from django.contrib import admin

from data_api.staging import models

admin.site.register(models.Organization)
admin.site.register(models.Group)
admin.site.register(models.Contact)
admin.site.register(models.Field)
admin.site.register(models.Channel)
admin.site.register(models.ChannelEvent)
