import urllib2, httplib
from BeautifulSoup import BeautifulSoup, SoupStrainer
import Queue
import re
import socket
import threading
import time
import functools
import cookielib
from django.utils.encoding import force_unicode

from django.conf import settings

class UnfetchableURLException(Exception):
    pass


class OffsiteLinkException(Exception):
    pass

class CannotHandleUrlException(Exception):
    pass


class memoize(object):
    """Decorator that caches a function's return value each time it is called.
       If called later with the same arguments, the cached value is returned, and
       not re-evaluated.
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            value = self.func(*args)
            self.cache[args] = value
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)
        def __repr__(self):
            """Return the function's docstring."""
            return self.func.__doc__
        def __get__(self, obj, objtype):
            """Support instance methods."""
            return functools.partial(self.__call__, obj)


STORE_CONTENT = getattr(settings, 'SPIDER_STORE_CONTENT', True)

domain_re = re.compile('(([a-z]+://)[^/\?]+)*')
subdomain_re = re.compile('([a-z]+://)(.*?\.)+([^\/\?]+\.[^\/\?\.]+([\/\?].*)?)')


def get_domain(url):
    match = re.search(domain_re, url)
    if match:
        return match.group()
    return ''

def get_host(url):
    domain = get_domain(url)
    if domain:
        return domain.split('://')[1]
    return ''

def relative_to_full(example_url, url):
    """
    Given a url which may or may not be a relative url, convert it to a full
    url path given another full url as an example
    """
    # remove any hashes
    url = re.sub('(#[^\/]+)', '', url)
    
    # does this url specify a protocol?  if so, it's already a full url
    if re.match('[a-z]+:\/\/', url):
        return url
    
    # if the url doesn't start with a slash it's probably relative to the
    # current url, so join them and return
    if not url.startswith('/'):
        # check to see if there is a slash after the protocol -- we'll use the
        # slash to determine the current working directory for this relative url
        if re.match('^[a-z]+:\/\/(.+?)\/', example_url):
            return '/'.join((example_url.rpartition('/')[0], url))
    
    # it starts with a slash, so join it with the domain if possible
    domain = get_domain(example_url)
    
    if domain:
        return '/'.join((domain, url.lstrip('/')))
    
    return url

def get_urls(content):
    # retrieve all link hrefs from html
    links = []
    try:
        link_soup = BeautifulSoup(content, parseOnlyThese=SoupStrainer('a'))
    except UnicodeEncodeError:
        return links
    for link in link_soup:
        if link.has_key('href'):
            links.append(link.get('href'))
    return links

def strip_subdomain(url):
    match = subdomain_re.search(url)
    if match:
        return subdomain_re.sub('\\1\\3', url)
    return url

@memoize
def is_on_site(source_url, url, domain_substring=None):
    if url.startswith('/'):
        return True
    
    
    if '://' not in url:
        if url.startswith('mailto') or url.startswith('javascript'):
            return False
        return True

    if domain_substring and domain_substring not in url:
        return False

    
    source_domain = get_domain(source_url)
    if not source_domain:
        raise ValueError('%s must contain "protocol://host"' % source_url)
    
    
    domain = get_domain(url)
    if domain and domain == source_domain:
        return True

    
    # try stripping out any subdomains
    if domain and strip_subdomain(domain) == strip_subdomain(source_domain):
        return True
    
    return False


#def fetch_url(url, timeout):
#    f = urllib2.urlopen(url, timeout=timeout)
#    res = f.read()
#    f.close()
#    return res


def ascii_hammer(content):
    return ''.join([c for c in content if ord(c) < 128])


class SpiderThread(threading.Thread):
    def __init__(self, url_queue, response_queue, finish_event, spider_profile):
        threading.Thread.__init__(self)

        self.url_queue = url_queue
        self.response_queue = response_queue
        self.finish_event = finish_event
        
        # load data from the session obj passed in
        self.source_url = spider_profile.base_url
        self.timeout = spider_profile.timeout
        self.profile = spider_profile
        self.extractor_class = self.profile.get_extractor_class()
        self.headers = {}
        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        #urllib2.install_opener(self.opener)

        self.working = False
    
    def run(self):
        if self.profile.login_url:
            self.login()
        
        while not self.finish_event.is_set():
            self.process_queue()
            if self.profile.delay:
                time.sleep(self.profile.delay)


    def login(self):
            #log in
            print "Logging in at", self.profile.login_url, "..."
            request = urllib2.Request(url=self.profile.login_url,
                                      data=self.profile.login_details,
                                      headers={})
            response = self.opener.open(request)

    
    def process_queue(self):
        try:
            self.working = True
            url, source, depth = self.url_queue.get_nowait()
        except Queue.Empty:
            self.working = False
            time.sleep(1)
        except KeyboardInterrupt:
            self.working = False
            return
        else:
            try:
                crawl_start = time.time()
                headers, content, urls = self.crawl(self.source_url, url, self.timeout)
                response_time = time.time() - crawl_start
            except (UnfetchableURLException, OffsiteLinkException, AttributeError, CannotHandleUrlException, httplib.BadStatusLine):
                pass
            else:
                if self.profile.logged_out_string and self.profile.logged_out_string in force_unicode(content, errors='ignore'):
                    self.login()
                    self.url_queue.put((url, source, depth))
                    self.working = False
                    return

                if 'content-length' not in headers:
                    headers['content-length'] = len(content)
                if 'status' not in headers:
                    headers['status'] = '200'   # ugh. how to get status from urllib2 in crawl()?
                    
                if not STORE_CONTENT:
                    content = ''
                    
                results = dict(
                    url=url,
                    source_url=source,
                    content=content,
                    response_status=int(headers['status']),
                    response_time=response_time,
                    content_length=int(headers['content-length']),
                    headers=headers,
                )
                self.response_queue.put((results, urls, depth))
            
            self.url_queue.task_done()
            
            
    def fetch_url(self, url, timeout):
        request = urllib2.Request(url=url,
                                  headers=self.headers)
        return self.opener.open(request, timeout=timeout)

    
    def crawl(self, source_url, url, timeout, log=True):
        try:
            if log:
                print "Going to url: %s" % url
            if not self.extractor_class.can_handle_url(url, self.opener):
                raise CannotHandleUrlException
        
            response = self.fetch_url(url, timeout)
            headers_raw = response.info().headers
            headers = {}
            for header in headers_raw:
                (k, s, v) = header.partition(":")
                headers[k] = v.strip()
            content = response.read()
        except socket.error:
            raise UnfetchableURLException
        except urllib2.URLError:
            raise UnfetchableURLException # should be other error
        
        if is_on_site(source_url, response.geturl()):
            urls = get_urls(content)
            return headers, content, self.filter_urls(url, urls)
        else:
            raise OffsiteLinkException
        
        return headers, content, []
    
    def filter_urls(self, source, urls):
        ret = []
        for url in urls:
            if self.profile.links_ignore_regex and re.search(self.profile.links_ignore_regex, url):
                continue
            if is_on_site(source, url, self.profile.domain):
                ret.append(relative_to_full(source, url))
        return ret