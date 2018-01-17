from django.conf.urls import patterns, url
from . import views

urlpatterns = patterns(
    '',
    url(r'^import_org/$', views.import_org_view),
)
