from django.core.management.base import BaseCommand
from magellan.models import SpiderProfile
import Queue
import BeautifulSoup
import threading
from magellan.utils import SpiderThread, import_class, get_backend
import sys
from django.conf import settings


class Command(BaseCommand):
    
    def handle(self, *args, **options):
        fast = False
        single_thread = False
        if 'help' in args:
            print "manage.py index [profile1 profile2 ...]"
            print "Extra options:"
            print "--fast: tell the backend to index quickly, possibly by lifting unique constraints."
            print "--single-thread: only use one thread to index, regardless of each profile's configuration"
            return
        if '--fast' in args:
            fast = True
            args.pop('--fast')
        if '--single-thread' in args:
            single_thread = True
            args.pop('--single-thread')

        if args:
            profiles = SpiderProfile.objects.filter(name__in=args)
        else:
            profiles = SpiderProfile.objects.filter(active=True)
        
        for profile in profiles:
            spider(profile, fast=fast, single_thread=single_thread)
            

def spider(profile, log=True, fast=False, single_thread=False):
    depth = profile.depth
    indexer = get_backend(fast=fast)
    indexer.create_index(profile.name)
    pending_urls = Queue.Queue()
    processed_responses = Queue.Queue(maxsize=50)
    finished = threading.Event()
    
    visited = {}
    scheduled = set()
    
    if not single_thread:
        thread_count = profile.threads or getattr(settings, 'SPIDER_THREADS', 4)
    else:
        thread_count = 1
        
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
        indexer.commit() #one last commit to ensure we don't lose the last few items.
    return visited

