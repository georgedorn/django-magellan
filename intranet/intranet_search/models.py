from django.db import models
from django.contrib import admin
from whoosh import fields, index
from whoosh.qparser import MultifieldParser
import os
from django.conf import settings
from django.utils.encoding import force_unicode

WHOOSH_SCHEMA = fields.Schema(title=fields.TEXT(stored=True),
                                                               content = fields.TEXT,
                                                               url=fields.ID(stored=True, unique=True),
                                                               site=fields.ID(stored=True, unique=False )
                                                               )

class SpiderProfile(models.Model):
    """
    Represents a site to spider.
    """
    name = models.CharField(max_length=255)
    base_url = models.CharField(max_length=255, help_text="Full URL to page to begin spidering")
    domain = models.CharField(max_length=255, help_text="Substring (of domain or otherwise) to limit links followed")
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

    def __unicode__(self):
        return u"%s - starting at: %s" % (self.name, self.base_url)

class SpiderProfileAdmin(admin.ModelAdmin):
    pass
admin.site.register(SpiderProfile, SpiderProfileAdmin)


class WhooshPageIndex(object):

    def create_index(self):
        path = settings.WHOOSH_INDEX
        if not os.path.exists(path):
            os.mkdir(path)
        self.ix = index.create_in(settings.WHOOSH_INDEX, schema=WHOOSH_SCHEMA)

    def open_index(self):
        self.ix = index.open_dir(settings.WHOOSH_INDEX)
    
    def commit(self, refresh_writer=True, *args, **kwargs):
        if self.writer is not None:
            self.writer.commit(*args, **kwargs)
        self.batch_count = 0
        if refresh_writer:
            self.writer = self.ix.writer()
        
    def __init__(self, batch_size=20):
        if os.path.exists(settings.WHOOSH_INDEX):
            self.open_index()
        else:
            self.create_index()
        self.writer = None
        self.batch_size = batch_size
        self.batch_count = 0
            
    def add_page(self, url, title, content, site, commit=False):
        """
        Adds or updates a page in the index.  url is unique; calling add_page with the same url will replace the existing document.
        """
        if self.writer is None:
                    self.writer = self.ix.writer()
        self.writer.update_document(title=unicode(title), content=unicode(content), url=unicode(url), site=unicode(site))
        self.batch_count += 1
        if commit or self.batch_count >= self.batch_size:
            self.commit()
            
    def search(self, query):
        parser = MultifieldParser(fieldnames=('content','title'), 
                                                    schema=self.ix.schema, 
                                                    fieldboosts={'content':1,'title':2})
        qry = parser.parse(query)
        search = self.ix.searcher()
#        with self.ix.searcher() as searcher:
        return search.search(qry)
            

        
            

            
    
        





        


    


