from django import forms
from django.conf import settings
from whoosh import index, store, fields
from django.shortcuts import render

from intranet_search.models import WhooshPageIndex



def search(request):
    page_index = WhooshPageIndex()
    query = request.GET.get('q', None)
    if query:
        query = query.replace('+', ' AND ').replace(' -', ' NOT ') #this is fairly lame
        results = page_index.search(query)
    
    return render(request, 'search_results.html', {'query':query, 'results':results})



