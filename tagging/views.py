#coding: utf-8
from __future__ import unicode_literals, absolute_import

import json

from django.http import JsonResponse
from django.utils.datastructures import MultiValueDictKeyError

from tagging.models import Tag


def tag_it_suggest(request):
    tags = []
    term = request.GET.get('term', None)
    if term is not None:
        qs = Tag.objects.filter(name__istartswith=term)

        namespace = request.GET.get('ns', None)
        if namespace is not None:
            qs = qs.filter(namespace=namespace)

        try:
            tags = qs.values_list('name', flat=True)
        except MultiValueDictKeyError:
            pass

    return JsonResponse([x.encode('utf-8') for x in tags])


def typeahead_suggest(request):
    tags = []
    post_body = json.loads(request.body)
    term = post_body.get('typeahead', None)
    if term is not None:
        qs = Tag.objects.filter(name__istartswith=term)

        namespace = request.GET.get('ns', None)
        if namespace is not None:
            qs = qs.filter(namespace=namespace)

        try:
            tags = qs.values_list('name', flat=True)
        except MultiValueDictKeyError:
            pass

    return JsonResponse({'tags':[{'tag': x.encode('utf-8')} for x in tags]})
