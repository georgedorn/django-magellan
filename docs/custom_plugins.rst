Custom Content Extraction Plugins
===========================================
.. highlight:: python

Magellan can extract content from nearly any site it spiders.  However, often only a small part of the site is relevant to searchers.  By only indexing the useful content from a page, whoosh's index can be reduced in size, searches will perform faster and result in fewer
erroneous results.

This is where content extractors come in.  Subclass the following class, overriding methods as needed.

.. automodule:: magellan.extractor
.. autoclass:: BaseExtractor
   :members:
   :inherited-members:
   :undoc-members:
