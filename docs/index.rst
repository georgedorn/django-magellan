.. Django-Magellan documentation master file, created by
   sphinx-quickstart on Fri Sep  9 11:37:51 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Django-Magellan's documentation!
===========================================

Contents:

.. toctree::
   :maxdepth: 2

   Getting Started <installation>
   custom_plugins
   internals
   
What is Magellan?
=================
Magellan is a 100% python search engine and spider app for django.  
Think of it as a mini intranet search appliance, but for the internet.

How does it work?
=================
Magellan spiders sites that you specify in the django admin, indexing page content via Whoosh.

Features
========

* Application agnostic.  Magellan will spider anything you have access to.
* Pure python.  No dependencies on external services like SOLR.
* Portable.  Load Magellan into a relocatable virtualenv and use sqlite, and you can carry your search engine on a usb drive.
* Multithreaded spidering, for speed.
* Naive and extensible.  Have a site you want to index?  Write your own content extractor to scrape just the parts you care about.
* Authenticates.  Currently supports form-based authentication.  Oauth and HTTP auth to follow.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

