from django.core.management.base import BaseCommand, CommandError
from django.utils.html import strip_tags
from intranet_search.models import WhooshPageIndex, SpiderProfile
import Queue
import urllib, urllib2
import BeautifulSoup
import threading
import time
from intranet_search.utils import UnfetchableURLException, OffsiteLinkException,\
    SpiderThread

from django.conf import settings


class Command(BaseCommand):
    
    def handle(self, *args, **options):
        if args:
            profiles = SpiderProfile.objects.filter(name__in=args)
        else:
            profiles = SpiderProfile.objects.filter(active=True)
        
        for profile in profiles:
            spider(profile)


def spider(profile, log=True):
    depth = profile.depth
    indexer = WhooshPageIndex()
    pending_urls = Queue.Queue()
    processed_responses = Queue.Queue()
    finished = threading.Event()
    
    visited = {}
    scheduled = set()
    
    thread_count = profile.threads or getattr(settings, 'SPIDER_THREADS', 4)
    
    threads = [SpiderThread(pending_urls, processed_responses, finished, profile) for x in range(thread_count)]
    
    pending_urls.put((profile.base_url, '', depth))
    scheduled.add(profile.base_url)
    
    extractor = profile.get_extractor()

    [t.start() for t in threads]

    try:
        while 1:
            try:
                # pull an item from the response queue
                result_dict, urls, depth = processed_responses.get(timeout=profile.timeout)
            except Queue.Empty:
                #check to see if any of the workers are still doing anything
                done = True
                for t in threads:
                    if t.working:
                        print "Thread %s is still working, not exiting" % t
                        done = False
                if done:
                    print "All threads done working"
                    finished.set()
                    break
            else:
                # save the result
                processed_url = result_dict['url']
                if log:
                    print "Adding page at url: %s, content length: %s to index" % (processed_url, len(result_dict['content']))
                
                raw_content = result_dict['content']
                title = extractor.get_title(raw_content)
                content = extractor.get_content(raw_content)
                
                
                indexer.add_page(url=processed_url, title=title, content=content, site=profile.name)
                # remove from the list of scheduled items
                scheduled.remove(processed_url)
                
                # store response status in the visited dictionary
                visited[processed_url] = result_dict['response_status']
                
                # enqueue any urls that need to be checked
                if depth > 0:
                    for url in urls:
                        if url not in visited and url not in scheduled:
                            scheduled.add(url)
                            pending_urls.put((url, processed_url, depth - 1))
                
    except KeyboardInterrupt:
        pass

    print "Cleaning up..."
    finished.set()
    [t.join() for t in threads]
    print "Optimizing index..."
    indexer.commit(optimize=True, refresh_writer=False)

    return visited

