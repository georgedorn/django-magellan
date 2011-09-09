Installation
===========================================
.. highlight:: bash

#. Create your search engine project in django::

    django-admin startproject example

#. Install magellan via your favorite package installer::

    pip install git+https://github.com/georgedorn/django-magellan.git
    
#. Add 'magellan' to your INSTALLED_APPS.  If you are not overriding the search_results.html template, also add 'pagination' to INSTALLED_APPS and 'pagination.middleware.PaginationMiddleware' to MIDDLEWARE_CLASSES.
#. In settings.py, configure::

    MAGELLAN_PLUGINS_MODULE_PATH = "example.plugins" 
    - Optional, if you want to provide site-specific content extractors.
    MAGELLAN_WHOOSH_INDEX = os.path.join(my_path, 'whoosh_site_index')
    - Where to store the Whoosh files.
    MAGELLAN_WHOOSH_MAX_MEMORY = 256 
    - Maximum memory (in MB) to use for Whoosh.  Bigger is faster..
    SPIDER_COOKIE_JAR = os.path.join(my_path, 'cookies')
    - Where to store auth cookies when spidering. 
#. Configure your database and install the models::

    python manage.py syncdb

#. Run your django server (manage.py runserver or however you deploy this)
#. In django's admin, configure one or more SearchProfile objects.
#. Invoke the spider via manage.py index (which can take the name of a profile as an argument)
#. Hook up the magellan search result view in your urls.py. (This will become an include eventually.)::
    
    url(r'^search/', 'magellan.views.search'),

