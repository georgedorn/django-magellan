from django.conf import settings
from .base import BaseBackend
#there's probably a better place for this, but cPickle hits the default 1000 limit when whoosh is trying to append items
import sys
sys.setrecursionlimit(100000)

WHOOSH_SCHEMA = fields.Schema(title=fields.TEXT(stored=True),
                                                               content = fields.TEXT(stored=True), #need to store in order to handle highlights
                                                               url=fields.ID(stored=True, unique=True),
                                                               content_hash=fields.ID(unique=True),
                                                               site=fields.ID(stored=True, unique=False ),
                                                               headings=fields.TEXT(), #index on extra headings/keywords to weight these more heavily
                                                               )


class WhooshPageIndex(BaseBackend):
    
    _writer = None    
    _unique_data = defaultdict(list) #holds non-committed unique data to detect collisions

    def setup():
        self.create_index()
        self.open_index()

    def create_index(self):
        path = settings.MAGELLAN_WHOOSH_INDEX
        if not os.path.exists(path):
            os.mkdir(path)
        self.ix = index.create_in(path, schema=WHOOSH_SCHEMA)

    def open_index(self):
        self.ix = index.open_dir(settings.MAGELLAN_WHOOSH_INDEX)
    
    def commit(self, *args, **kwargs):
        if self.optimize_count > self.optimize_size:
            print "Optimizing index..."
            kwargs['optimize'] = True
            self.optimize_count = 0
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
    
    def __init__(self, batch_size=20, optimize_size=1000):
        if os.path.exists(settings.MAGELLAN_WHOOSH_INDEX):
            self.open_index()
        else:
            self.create_index()
        self.batch_size = batch_size
        self.batch_count = 0
        self.optimize_count = 0
        self.optimize_size = optimize_size
            
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
        self.optimize_count += 1
        if commit or self.batch_count >= self.batch_size:
            self.commit()
            
    def search(self, query, *args, **kwargs):
        parser = MultifieldParser(fieldnames=('content','title','headings','url'), 
                                                    schema=self.ix.schema, 
                                                    fieldboosts={'content':1,'title':2,'headings':3,'url':1})
        qry = parser.parse(query)
        search = self.ix.searcher()
#        with self.ix.searcher() as searcher:
        return search.search_page(qry, *args, **kwargs)
            

