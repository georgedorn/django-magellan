from pyelasticsearch import ElasticSearch
from pyelasticsearch.client import ConnectionError
from django.conf import settings
from collections import defaultdict
import hashlib
import math
from .base import BaseBackend

class ElasticSearchBackend(BaseBackend):
    
    def __init__(self, es_url='http://localhost:9200/', batch_size=10, **kwargs):
        """
        Do what is necessary to create/open the index.
        """
        self.batch_size = batch_size
        self.batch_count = 0
        self.es_url = es_url
        self.fast = kwargs.get('fast', False)
        if kwargs.get('noisy', False):
            from logging import getLogger, StreamHandler, DEBUG
            import sys
            logger = getLogger('pyelasticsearch')
            logger.setLevel(DEBUG)
            logger.addHandler(StreamHandler(sys.stdout))
            
        self.es = ElasticSearch(self.es_url)
        try:
            self.es.count('*')
        except ConnectionError:
            print "Error connecting to ElasticSearch server!"
            raise
        self.urls = defaultdict(set) #track urls to be deleted before committing new content
        self.batches = defaultdict(list) #site: [list of docs]
    
    def create_index(self, name):
        name = name.lower()
        try:
            self.es.create_index(name)
            self.update_mapping(name)
        except Exception, e:
            print e
            return
    
    def update_mapping(self, name):
        #update the ES mapping, which is roughly equivalent to a schema
        mapping = {"page":
                   {"properties":
                    {"content":{"type":"string", 'boost':1.0},
                     "hash":{"type":"string"},
                     "headings":{"type":"string", 'boost':3.0},
                     "title":{"type":"string", 'boost': 5.0},
                     "site":{'type':'string', 'index':'not_analyzed'},
                     "url":{"type":"multi_field",
                            "fields": {
                                "url": {"type":"string", "index":"analyzed"},
                                "exact": {"type":"string", "index":"not_analyzed"}
                                }
                            }
                     }
                    }
                   }
        self.es.put_mapping(name, 'page', mapping)
        
   
    def add_page(self, url, title, content, site, headings='', commit=False):
        """
        Adds a page to the index and commits the batch if specified.
        """
        hsh = self._hash(content)
        doc = {'url': url,
               'site': site,
               'title': title,
               'content': content,
               'headings':headings,
               'hash':hsh}
        self.urls[site].add(url)
        self.batches[site].append(doc)
        self.batch_count += 1
        
        if commit or self.batch_count > self.batch_size:
            self.commit()
            
    def delete_by_url(self, site, url):
        """
        Hack for inability to specify more than one key field.
        """
        #@todo: When pyelasticsearch's delete_by_query works, use it here
        results = self.es.search(index=site.lower(), doc_type='page', query={'query':{'term':{'url.exact':url}}})
        ids = [hit['_id'] for hit in results['hits']['hits']]
        for id in ids:
            print "Deleting %s" % id
            self.es.delete(index=site.lower(), doc_type='page', id=id)

    def commit(self):
        print "Committing."
        if not self.fast:
            #nuke things in this batch in case the content changed
            for site, urls in self.urls.items():
                for url in urls:
                    self.delete_by_url(site, url)

        for site, docs in self.batches.items():
            self.es.bulk_index(index=site.lower(), 
                               doc_type='page',
                               docs=docs,
                               id_field='hash') #id_field=hash ensure uniqueness
        self.batches = defaultdict(list) #reset docs
        self.urls = defaultdict(set) #reset urls
        self.batch_count = 0

    def _hash(self, content):
        content = unicode(content)
        hsh = "%s" % (hashlib.sha1(content.encode('utf-8')).hexdigest())
        return hsh
        
    
    def search(self, query, *args, **kwargs):
        """
        Performs a search and returns results.
        @todo: Need to figure out how to wildcard indexes (aka sites) or otherwise provide them here.
        Expected format of results:
        {'pagecount': int,
         'hits': [
         
            {'title': string,
             'highlights': string,
             'url': string
            }
         ]}
        """
        pagenum = kwargs.pop('pagenum', 1)
        per_page = kwargs.pop('pagelen', 100)
        sites = kwargs.pop('sites', None)
        if sites is not None:
            site_names = ','.join([site.lower() for site in sites])
        else:
            site_names = '_all'
        start = (pagenum-1)*per_page
        size = per_page
        es_query = {'from':start,
                    'size':size,
                    'query': 
                        {'filtered':
                            {'query':
                                {'query_string':
                                    {'query':query}
                                }
                            }
                        },
                     'highlight': 
                        {'pre_tags':['<b>', '<font color="blue">'],
                         'post_tags':['</b>', '</font>'],
                         'fields':
                            {'content': {}}
                            
                        }
                    }


        results = self.es.search(index=site_names, query=es_query)
        ret = {'hits':[]}
        total_hits = results['hits']['total']
        for res in results['hits']['hits']:
            row = res['_source']
            row['score'] = res['_score']
            row['highlight'] = '... '.join([h for h in res['highlight']['content']])
            ret['hits'].append(row)
        ret['pagecount'] = int(math.ceil(float(total_hits) / float(per_page)))
        ret['total_hits'] = total_hits
        return ret
    
    