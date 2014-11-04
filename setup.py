from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt')

reqs = [str(ir.req) for ir in install_reqs]

setup(
      name="DjangoMagellan",
      version="0.2",
      packages=find_packages(),
      install_requires=reqs,
      include_package_data=True,
      )
