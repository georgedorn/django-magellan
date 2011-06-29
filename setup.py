from setuptools import setup, find_packages

setup(
      name="DjangoMagellan",
      version="0.1",
      packages=find_packages(),
      install_requires=[
                        'BeautifulSoup>=3.2.0',
                        'Django>=1.3',
                        'Whoosh>=1.8.2',
                        'chardet>=1.0.1',
                        'django-pagination>=1.0.7',
                        ],
 
      include_package_data = True,
      )





