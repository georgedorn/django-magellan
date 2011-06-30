from django.core.management.base import BaseCommand
from magellan.models import WhooshPageIndex, SpiderProfile
import Queue
import BeautifulSoup
import threading
from magellan.utils import SpiderThread

from django.conf import settings

#there's probably a better place for this, but cPickle hits the default 1000 limit when whoosh is trying to append items
import sys
sys.setrecursionlimit(100000)



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
    processed_responses = Queue.Queue(maxsize=500)
    finished = threading.Event()
    
    visited = {}
    scheduled = set()
    
    thread_count = profile.threads or getattr(settings, 'SPIDER_THREADS', 4)
    
    threads = [SpiderThread(pending_urls, processed_responses, finished, profile) for _ in range(thread_count)]
    
    pending_urls.put((profile.base_url, '', depth))
    scheduled.add(profile.base_url)
    
    extractor = profile.get_extractor_class()

    [t.start() for t in threads]
    processed_url = None
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
                
                raw_content = result_dict['content']
                unicode_content = BeautifulSoup.UnicodeDammit(raw_content, isHTML=True).unicode
                
                e = extractor(unicode_content)
                if e.content_type == 'raw_ascii' and not getattr(settings, 'MAGELLAN_INDEX_RAW_ASCII', False):
                    if log:
                        print "Skipping page at url: %s, no means of extracting content" % processed_url
                    continue #don't index
                title = e.get_title()
                content = e.get_content()
                headings = e.get_headings()
                if log:
                    print "Adding page at url: %s, content length: %s to index" % (processed_url, len(content))
                
                
                indexer.add_page(url=processed_url, title=title, content=content, site=profile.name, headings=headings)
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
    except Exception, e:
        print "Got an exception while indexing page: %s\nWill exit." % processed_url
        raise

    finally:
    
        print "Cleaning up..."
        finished.set()
        [t.join() for t in threads]
        if len(visited) > 0:
            print "Optimizing index..."
            indexer.commit(optimize=True)
    
    return visited

