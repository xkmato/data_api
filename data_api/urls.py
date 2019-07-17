"""data_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

from rest_framework.authtoken import views
from rest_framework_swagger.views import get_swagger_view

from data_api.staging_api import urls as staging_api_urls

schema_view = get_swagger_view(title='RapidPro Data Warehouse API')

urlpatterns = [
    url(r'^api-token-auth/', views.obtain_auth_token),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/v3/', include(staging_api_urls)),
    url(r'^ui/', include('data_api.ui.urls')),
    url(r'^', schema_view),
]

handler404 = 'data_api.views.page_not_found_view'
handler500 = 'data_api.views.server_error_view'
handler403 = 'data_api.views.request_forbidden_view'
handler400 = 'data_api.views.bad_request_view'
