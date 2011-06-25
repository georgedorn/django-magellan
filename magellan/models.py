from django.db import models
from django.contrib import admin
from whoosh import fields, index
from whoosh.qparser import MultifieldParser
import os
from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils import importlib
import hashlib
from collections import defaultdict
from extractor import BaseExtractor

WHOOSH_SCHEMA = fields.Schema(title=fields.TEXT(stored=True),
                                                               content = fields.TEXT(stored=True), #need to store in order to handle highlights
                                                               url=fields.ID(stored=True, unique=True),
                                                               content_hash=fields.ID(unique=True),
                                                               site=fields.ID(stored=True, unique=False ),
                                                               headings=fields.TEXT(), #index on extra headings/keywords to weight these more heavily
                                                               )

class SpiderProfile(models.Model):
    """
    Represents a site to spider.
    """
    name = models.CharField(max_length=255)
    base_url = models.CharField(max_length=255, help_text="Full URL to page to begin spidering")
    domain = models.CharField(max_length=255, help_text="Substring (of domain or otherwise) to limit links followed", blank=True)
    depth = models.IntegerField(default=0, help_text="How many pages deep to follow links; 0 for infinite")
    active = models.BooleanField(default=True)
    timeout = models.IntegerField(default=30, help_text="Maximum time, per page, to wait for a response")
    login_url = models.CharField(max_length=255, 
                                                        help_text="URL to POST credentials to; not the login form itself, but the action of the form",
                                                        blank=True)
    login_details = models.CharField(max_length=255,
                                                        help_text="urlencoded data to post to URL; e.g. name=foo&password=bar",
                                                        blank=True)
    logged_out_string = models.CharField(max_length=255,
                                                        help_text="String to search for on response page to detect logged out status",
                                                        blank=True)
    threads = models.IntegerField(default=1, help_text="How many threads to use when spidering this site")
    delay = models.IntegerField(default=0, help_text="How long to wait between requests, for each thread")    
    links_ignore_regex = models.CharField(max_length=255,
                                                        help_text="Links matching this regex will not be followed",
                                                        blank=True)
    extraction_plugin = models.CharField(max_length=255,
                                                        help_text="Module name containing an implementation of BaseExtractor with same name as module.",
                                                        blank=True)
    
    def get_extractor_class(self):
        """
        Dynamically imports a the module+class specified by extraction_plugin and returns an instance of it.
        Or returns the BaseExtractor, if none is set.
        """
        if not self.extraction_plugin:
            return BaseExtractor
        
        module_name = settings.MAGELLAN_PLUGINS_MODULE_PATH
        module = importlib.import_module(name=module_name)
        cls = getattr(module, self.extraction_plugin)
        return cls
        
    def __unicode__(self):
        return u"%s - starting at: %s" % (self.name, self.base_url)

class SpiderProfileAdmin(admin.ModelAdmin):
    pass
admin.site.register(SpiderProfile, SpiderProfileAdmin)



        
class WhooshPageIndex(object):
    
    _writer = None    
    _unique_data = defaultdict(list) #holds non-committed unique data to detect collisions

    def create_index(self):
        path = settings.MAGELLAN_WHOOSH_INDEX
        if not os.path.exists(path):
            os.mkdir(path)
        self.ix = index.create_in(path, schema=WHOOSH_SCHEMA)

    def open_index(self):
        self.ix = index.open_dir(settings.MAGELLAN_WHOOSH_INDEX)
    
    def commit(self, *args, **kwargs):
        self.writer.commit(*args, **kwargs)
        self.batch_count = 0
        self._unique_data = defaultdict(list)
    
    @property
    def writer(self):
        if self._writer and not self._writer.is_closed:
            return self._writer
        memory = getattr(settings, 'MAGELLAN_WHOOSH_MAX_MEMORY', 32)
        self._writer = self.ix.writer(limitmb=memory)
        return self._writer
    
    def __init__(self, batch_size=20):
        if os.path.exists(settings.MAGELLAN_WHOOSH_INDEX):
            self.open_index()
        else:
            self.create_index()
        self.batch_size = batch_size
        self.batch_count = 0
            
    def add_page(self, url, title, content, site, headings='', commit=False):
        """
        Adds or updates a page in the index.  url is unique; calling add_page with the same url will replace the existing document.
        """
        content = unicode(content)
        hash = "%s:%s" % (site, hashlib.sha1(content.encode('utf-8')).hexdigest())
        
        if hash in self._unique_data['hash'] or url in self._unique_data['url']:
            print "Duplicate data in batch detected"
            self.commit()
        
        self._unique_data['hash'].append(hash)
        self._unique_data['url'].append(url)
        
        self.writer.update_document(title=force_unicode(title), 
                                                          content=force_unicode(content), 
                                                          url=force_unicode(url), 
                                                          site=force_unicode(site), 
                                                          content_hash=force_unicode(hash),
                                                          headings=force_unicode(headings))
        self.batch_count += 1
        if commit or self.batch_count >= self.batch_size:
            self.commit()
            
    def search(self, query, *args, **kwargs):
        parser = MultifieldParser(fieldnames=('content','title','headings','url'), 
                                                    schema=self.ix.schema, 
                                                    fieldboosts={'content':1,'title':2,'headings':3,'url':1})
        qry = parser.parse(query)
        search = self.ix.searcher()
#        with self.ix.searcher() as searcher:
        return search.search(qry, *args, **kwargs)
            

        
            

            
    
        





        


    


