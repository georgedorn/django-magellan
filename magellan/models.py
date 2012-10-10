from django.db import models
from django.contrib import admin
import os
from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils import importlib
from django import forms
import hashlib
from collections import defaultdict
from extractor import BaseExtractor


class SpiderProfile(models.Model):
    """
    Represents a site to spider.
    """
    name = models.CharField(max_length=255)
    base_url = models.CharField(max_length=255, help_text="Full URL to page to begin spidering")
    domain = models.CharField(max_length=255, help_text="Substring (of domain or otherwise) to limit links followed", blank=True)
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
    threads = models.IntegerField(default=1, 
                                  help_text="How many threads to use when spidering this site")
    delay = models.IntegerField(default=0, 
                                help_text="How long to wait between requests, for each thread")    
    links_ignore_regex = models.CharField(max_length=255,
                                          help_text="Links matching this regex will not be followed",
                                          blank=True)
    extraction_plugin = models.CharField(max_length=255,
                                         help_text="Module name containing an implementation of BaseExtractor with same name as module.",
                                         blank=True)
    
    def get_extractor_class(self):
        """
        Dynamically imports a the module+class specified by extraction_plugin and returns an instance of it.
        Or returns the BaseExtractor, if none is set.
        """
        if not self.extraction_plugin:
            return BaseExtractor
        
        module_name = settings.MAGELLAN_PLUGINS_MODULE_PATH
        module = importlib.import_module(name=module_name)
        cls = getattr(module, self.extraction_plugin)
        return cls
        
    def __unicode__(self):
        return u"%s - starting at: %s" % (self.name, self.base_url)

class SpiderProfileAdminForm(forms.ModelForm):
    class Meta:
        model = SpiderProfile
        widgets = {
                   'login_details': forms.TextInput(attrs={'size': '3'})
                   }

class SpiderProfileAdmin(admin.ModelAdmin):
    form = SpiderProfileAdminForm

admin.site.register(SpiderProfile, SpiderProfileAdmin)
        
            

            
    
        





        


    


