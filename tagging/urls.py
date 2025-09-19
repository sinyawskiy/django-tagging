#coding: utf-8
from __future__ import unicode_literals, absolute_import
from tagging.views import tag_it_suggest, typeahead_suggest
try:
    from django.conf.urls import url
except ImportError:
    from django.urls import re_path as url

app_name = 'tagging'
urlpatterns = [
    url(r'^tagit-suggest/$', tag_it_suggest, name='tagit-suggest'),
    url(r'^typeahead-suggest/$', typeahead_suggest, name='typeahead-suggest'),
]
