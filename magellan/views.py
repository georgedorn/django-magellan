from django import forms
from django.conf import settings
from whoosh import index, store, fields
from django.shortcuts import render
from magellan.models import WhooshPageIndex, SpiderProfile

def search(request):
    profiles = SpiderProfile.objects.filter(active=True)
    vars = {'profiles':profiles} 
    
    page_index = WhooshPageIndex()
    query = request.GET.get('q', None)
    if query:
        query = query.replace('+', ' AND ').replace(' -', ' NOT ') #this is fairly lame
        results = page_index.search(query, limit=100)
        vars['query'] = query
        vars['results'] = [ dict(title=r['title'], highlight=r.highlights('content'), url=r['url']) for r in results]
        vars['num_results'] =len(results)
        
    return render(request, 'search_results.html', vars)


