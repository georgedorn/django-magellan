import re
from django.utils.html import strip_tags
import BeautifulSoup
from magellan.utils import ascii_hammer
try:
    from pyPdf import PdfFileReader
except ImportError:
    PdfFileReader = None
import StringIO


class BaseExtractor(object):
    """
    Used to extract titles, content and urls from pages crawled in this profile.
    """
    content_type = None
    soup = None
    
    def __init__(self, content):
        self.content = content

        if content.startswith("%PDF"):
            if PdfFileReader is not None:
                sio = StringIO.StringIO(content)
                try:
                    self.reader = PdfFileReader(sio)
                    self.content = ' '.join([page.extractText() for page in self.reader.pages])
                    self.content_type = 'pdf'
                except Exception: #pyPdf's exceptions are not awesome.
                    self.reader = None
                    self.content = content
                    
        if not self.content_type:      
            try:
                self.soup = BeautifulSoup.BeautifulSoup(self.content)
                self._strip_script()
                self._strip_style()
                self._strip_doctype_and_comments()
                self.content_type = 'html'
            except UnicodeEncodeError:
                self.soup = None

        if not self.content_type:
            self.content_type = 'raw_ascii'
                
    @staticmethod
    def can_handle_url(url, opener):
        """
        Method to determine whether a given url can be handled by this extractor.
        Can make deductions based on the url itself, or can use the url opener to examine headers.
        """
        return True
            
    
    def get_title(self):
        if self.content_type == 'pdf':
            try:
                return self.reader.documentInfo['/Title']
            except:
                pass
        
        try:
            title = self.soup.html.head.title.string
        except:
            title = "No Title"
        return title
    
    def get_content(self):
        if self.content_type == 'html' and self.soup:
            content = strip_tags(self.soup.getText(separator=' '))
        elif self.content_type == 'pdf':
            return self._strip_whitespace(self.content)
        else:
            #this is incredibly brutal.  
            #we should try much harder to handle crazy weird content (e.g. PDFs)
            #before descending to these depths of barbarism
            content = strip_tags(ascii_hammer(self.content))

        return self._strip_whitespace(content)
    
    def get_headings(self):
        if not self.soup:
            return ''
        headings = []
        for tag in ('h1','h2','h3'):
            hs = [h.string for h in self.soup.findAll(tag) if h.string is not None]
            headings.extend(hs)
        return ' '.join(headings)
    
    def _strip_script(self):
        to_extract = self.soup.findAll('script')
        for item in to_extract:
            item.extract()

    

    def _strip_style(self):
        to_extract = self.soup.findAll('style')
        for item in to_extract:
            item.extract()

    def _strip_whitespace(self, content):
        return re.sub('\s+', ' ', content)
    
    def _strip_doctype_and_comments(self):
        comments = self.soup.findAll(text=lambda text:isinstance(text, BeautifulSoup.Comment))
        [comment.extract() for comment in comments] 
        for child in self.soup.contents:
            if isinstance(child, BeautifulSoup.Declaration):
                if child.string.lower().startswith('doctype'):
                    child.extract()
                    
                    
    def strip_by_ids(self, ids):
        """Removes elements from the soup that match any id in the provided list"""
        ids_string = '(%s)' % '|'.join(ids)
        ids_regex = re.compile(ids_string)
        
        elements = self.soup.findAll(id=ids_regex)
        [e.extract() for e in elements]

    def strip_by_classes(self, classes):
        """Removes elements from the soup that match any id in the provided list"""
        classes_string = '(%s)' % '|'.join(classes)
        classes_regex = re.compile(classes_string)
        
        elements = self.soup.findAll(attrs={'class':classes_regex})
        [e.extract() for e in elements]

        
