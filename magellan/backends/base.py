

class BaseBackend(object):
    
    def __init__(self, *args, **kwargs):
        """
        Do what is necessary to create/open the index.
        """
        raise NotImplementedError
   
    def add_page(self, url, title, content, site, headings='', commit=False):
        """
        Adds a page to the index and commits the batch if specified.
        """
        raise NotImplementedError
    
    def search(self, query, *args, **kwargs):
        """
        Performs a search and returns results.
        """
        raise NotImplementedError
    
    
    