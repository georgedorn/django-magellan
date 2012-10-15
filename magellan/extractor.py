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
                self.strip_script()
                self.strip_style()
                self.strip_doctype_and_comments()
                self.content_type = 'html'
            except UnicodeEncodeError:
                self.soup = None

        if not self.content_type:
            self.content_type = 'raw_ascii'
    
    @classmethod        
    def get_urls(cls, content):
        # retrieve all link hrefs from html
        links = []
        try:
            link_soup = BeautifulSoup.BeautifulSoup(content, parseOnlyThese=BeautifulSoup.SoupStrainer('a'))
        except UnicodeEncodeError:
            return links
        for link in link_soup:
            if link.has_key('href'):
                links.append(link.get('href'))
        return cls.clean_urls(links)

    @classmethod
    def clean_urls(cls, urls):
        fixed_urls = [cls.fix_url(url) for url in urls]
        fixed_urls = list(set(fixed_urls)) #throw out dupes
        return fixed_urls


    @classmethod
    def fix_url(cls, url):
        """
        Clean up urls with /../ or /./ in them, as well as other minor tweaks.
        This fixes them, popping off both the .. and the path component above it, and
        removes . entirely.
        """
        regex = r'[^./]+/\.\.\/'
        new_url, count = re.subn(regex, '', url)
        while count > 0:
            new_url, count = re.subn(regex, '', new_url)
        
        regex2 = r'/\./'
        new_url, count = re.subn(regex2, '', new_url)
        while count > 0:
            new_url, count = re.subn(regex2, '', new_url)

        new_url = new_url.strip('#!') #remove extra # chars at end of url 
        
        return new_url


                
    @staticmethod
    def can_handle_url(url, opener):
        """
        Determines whether a given url can be handled by this extractor.
        Can make deductions based on the url itself, or can use the url opener to examine headers.
        """
        return True
            
    
    def get_title(self):
        """
        Returns the title from the document's content.
        Override to trim title or otherwise mutate the title.
        Used by the indexer when adding documents to the search index.
        """
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
        """
        Returns the content of the document in a format suitable
        for indexing.  By default, strips html tags extra whitespace.
        Override to strip out more superfluous content, such as sidebars, headers,
        footers, etc.
        """
        if self.content_type == 'html' and self.soup:
            content = strip_tags(self.soup.getText(separator=' '))
        elif self.content_type == 'pdf':
            return self.strip_whitespace(self.content)
        else:
            #this is incredibly brutal.  
            #we should try much harder to handle crazy weird content (e.g. PDFs)
            #before descending to these depths of barbarism
            content = strip_tags(ascii_hammer(self.content))

        return self.strip_whitespace(content)
    
    def get_headings(self):
        """
        Headings are indexed an additional time from normal content, 
        as these are likely important clues to the document's content.
        Override if headings are not just h1, h2 or h3 tags.
        """
        if not self.soup:
            return ''
        headings = []
        for tag in ('h1','h2','h3'):
            hs = [h.string for h in self.soup.findAll(tag) if h.string is not None]
            headings.extend(hs)
        return ' '.join(headings)
    
    def strip_script(self):
        """
        Removes all script tags from html content.
        """
        to_extract = self.soup.findAll('script')
        for item in to_extract:
            item.extract()

    def strip_style(self):
        """
        Removes all style tags from html content.
        """
        to_extract = self.soup.findAll('style')
        for item in to_extract:
            item.extract()

    def strip_whitespace(self, content):
        """
        Returns content with duplicate whitespace converted to single spaces.
        """
        return re.sub('\s+', ' ', content)
    
    def strip_doctype_and_comments(self):
        """
        Removes doctype and HTML comments from HTML content.
        """
        comments = self.soup.findAll(text=lambda text:isinstance(text, BeautifulSoup.Comment))
        [comment.extract() for comment in comments] 
        for child in self.soup.contents:
            if isinstance(child, BeautifulSoup.Declaration):
                if child.string.lower().startswith('doctype'):
                    child.extract()
                    
                    
    def strip_by_ids(self, ids):
        """
        A helper method for trimming content.
        Removes elements from the HTML content that match any id in the provided list
        """
        ids_string = '(%s)' % '|'.join(ids)
        ids_regex = re.compile(ids_string)
        
        elements = self.soup.findAll(id=ids_regex)
        [e.extract() for e in elements]

    def strip_by_classes(self, classes):
        """
        A helper method for trimming content.
        Removes elements from the soup that match any class in the provided list
        """
        classes_string = '(%s)' % '|'.join(classes)
        classes_regex = re.compile(classes_string)
        
        elements = self.soup.findAll(attrs={'class':classes_regex})
        [e.extract() for e in elements]

        
