from django.conf.urls import url

from . import views

urlpatterns = (
    url(r'^import_org/$', views.import_org_view),
)
