from django.db import models
from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse

from magellan.models import (
    BaseContentSubscription,
    ContentDoesNotExist,
    ContentUnavailable
)

from pytumblr import TumblrRestClient


class TumblrError(ContentUnavailable):
    pass


class TumblrNotFound(ContentDoesNotExist):
    pass


class TumblrSubscription(BaseContentSubscription):
    """
    A subscription to tumblr content.
    """
    tumblr_username = models.CharField(max_length=255,
                help_text="Tumblr username you wish to index the friends of.")
    last_post_ts = models.BigIntegerField(null=True, blank=True)
    maximum_post_count = models.IntegerField(
        help_text="Maximum number of posts to index; 0 for infinite",
        default=0,
    )
    avatar = models.CharField(max_length=255, blank=True)
    pretty_name = models.CharField(max_length=255, blank=True)

    def _make_client(self):
        """
        Creates a tumblr client and read the blog's info to
        verify it exists and gets metadata.
        """
        client = TumblrRestClient(consumer_key=settings.TUMBLR_API_KEY)
        blog_info_raw = client.blog_info(self.tumblr_username)

        if 'meta' in blog_info_raw.keys():
            e_msg = "Status %s - %s" % (blog_info_raw['meta']['status'],
                                        blog_info_raw['meta']['msg'])
            if int(blog_info_raw['meta']['status']) == 404:
                raise TumblrNotFound(e_msg)
            else:
                raise TumblrError(e_msg)

        client.tumblr_info = blog_info_raw['blog']
        return client

    def get_content(self):
        """
        Get new blog entries from tumblr.
        """
        client = self._make_client()
        post_list = []

        # Step 1: check if updated, if not, bail early
        if(client.tumblr_info['updated'] <= self.last_post_ts):
            return post_list

        #save this for when we're done, to bookmark where we left off
        new_last_post_ts = client.tumblr_info['updated']

        # Step 2: Repeatedly get posts from blog 
        done_queueing = False

        while not done_queueing:
            #@todo:  there's a possibility of duplicate (and lost) entries in the rare case
            #that there are more than 20 new blog entries and another one is published
            #between our requests for more.  We should grab even more at a time to minimize the chances,
            #and if dupes are detected either start over, figure out where missing ones might be,
            #or just come up with a better approach to this entirely.
            resp = client.posts(self.short_name,
                                limit=20,
                                offset=len(post_list))
            twenty_posts = resp['posts']
            if len(twenty_posts) < 20:
                done_queueing = True  # we hit the last message in this request, so stop when done processing this batch
            for post in twenty_posts:
                # Step 3: and stop when we see one <= self.subscription.last_poll_time
                if post['timestamp'] > new_last_post_ts:
                    new_last_post_ts = post['timestamp'] #in the rare chance that a new entry was posted between the first request and this one

                if post['timestamp'] <= self.last_post_ts:
                    done_queueing = True #checked by while loop
                    break
                else:
                    post_list.append(post)

            if (self.maximum_post_count
                and len(post_list) > self.maximum_post_count):
                done_queueing = True

        if new_last_post_ts != self.last_post_ts:
            self.last_post_ts = new_last_post_ts
            self.save()
        return post_list

    def pull_metadata(self, save=False):
        """
        Get info about the blog from Tumblr; not the content.
        """
        client = self._make_client()

        # Get avatar
        self.avatar = client.avatar(self.short_name)['avatar_url']

        # Get blog pretty_name
        self.pretty_name = client.tumblr_info['title']

        # Get most recent post's timestamp
        self.last_post_ts = client.tumblr_info['updated']

        if save is True:
            self.save()

    def save(self, *args, **kwargs):
        # check if it looks like this is a brand new object, if so, pull the
        # data from tumblr
        if not self.avatar and not self.pretty_name:
            self.pull_metadata()

        super(TumblrSubscription, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('subscription_detail_tumblr', kwargs={'pk':self.pk})

    def __unicode__(self):
        # so it's intelligible in the django admin
        return "%s (Tumblr) sub for %s, c/o %s" % (self.short_name, self.recipient, self.recipient.sender)

admin.site.register(TumblrSubscription)
