from django import forms
from django.conf import settings
from whoosh import index, store, fields
from django.shortcuts import render
from magellan.models import WhooshPageIndex, SpiderProfile
from datetime import datetime

class SearchForm(forms.Form):
    query = forms.CharField(max_length=100)
    profiles = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)
    
    def __init__(self, *args, **kwargs):
        profiles = SpiderProfile.objects.filter(active=True)
        profile_choices = [(p.pk, p.name) for p in profiles]
        self.base_fields['profiles'].choices = profile_choices
        self.base_fields['profiles'].initial = [p[0] for p in profile_choices]
        super(SearchForm, self).__init__(*args, **kwargs)
        


def search(request):
    vars = {}
    if request.GET.get('query'):
        #form was submitted
        page = int(request.GET.get('page', 1))
        search_form = SearchForm(request.GET)
        query = search_form['query'].value().replace('+', ' AND ').replace(' -', ' NOT ')
        
        profile_ids = search_form['profiles'].value()
        if profile_ids and len(profile_ids) != len(search_form['profiles'].field.choices):
            profiles = SpiderProfile.objects.filter(active=True).filter(pk__in=profile_ids)
            query = "(%s) AND (%s)" % (query, ' OR '.join(['site:%s' % p.name for p in profiles] ))
        
        page_index = WhooshPageIndex()
        start_time = datetime.now()
        results = page_index.search(query, pagenum=page, pagelen=100)
        query_time = datetime.now() - start_time
        query_time_formatted = float(query_time.seconds) + float(query_time.microseconds)/1000000.0 
        vars['query_time'] = query_time_formatted
        vars['page'] = page
        vars['pagecount'] = results.pagecount
        vars['results'] = [ dict(title=r['title'], highlight=r.highlights('content'), url=r['url']) for r in results]
        vars['pagination_results'] = range(1, len(results))
        vars['num_results'] = len(results)
        template = 'search_results.html'
    else:
        search_form = SearchForm()
        template = 'index.html'
    
    vars['search_form'] = search_form 
    return render(request, template, vars)


