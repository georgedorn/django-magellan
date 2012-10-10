from pyelasticsearch import ElasticSearch
from django.conf import settings
from collections import defaultdict
import hashlib

class ElasticSearchBackend(object):
    
    def __init__(self):
        """
        Do what is necessary to create/open the index.
        """
        self.es_url = getattr(settings, 'http://localhost:9200/')
        self.es = ElasticSearch(self.es_url)
        self.batches = defaultdict(list) #site: [list of docs]
        
   
    def add_page(self, url, title, content, site, headings='', commit=False):
        """
        Adds a page to the index and commits the batch if specified.
        """
        hsh = self._hash(content)
        doc = {'url': url,
               'title': title,
               'content': content,
               'headings':headings,
               'hash':hsh}

        self.batches[site].append(doc)
        
        if commit:
            for site, docs in self.batches.items():
                self.es.bulk_index(index=site, 
                                   doc_type='page',
                                   docs=docs,
                                   id_field='hash') #id_field=hash ensure uniqueness
        self.batches = defaultdict(list) #reset docs
                

    def _hash(self, content):
        content = unicode(content)
        hsh = "%s" % (hashlib.sha1(content.encode('utf-8')).hexdigest())
        return hsh
        
    
    def search(self, query, *args, **kwargs):
        """
        Performs a search and returns results.
        @todo: Need to figure out how to wildcard indexes (aka sites) or otherwise provide them here.
        """
        
        return self.es.search(indexes=None)
        
    
    