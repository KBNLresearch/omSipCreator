#!/usr/bin/env python

import codecs
import os
import re
import sys

from setuptools import setup, find_packages

def read(*parts):
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

install_requires = [
    'requests',
    'setuptools',
    'lxml',
    'pypiwin32'
]

setup(name='omSipCreator',
      packages=find_packages(),
      version=find_version('omSipCreator', 'omSipCreator.py'),
      license='Apache License 2.0',
      platforms=['POSIX', 'Windows'],
      description='Create ingest-ready SIPs from batches of optical media images',
      long_description='Create ingest-ready SIPs from batches of optical media images',
      author='Johan van der Knijff',
      author_email='johan.vanderknijff@kb.nl',
      maintainer='Johan van der Knijff',
      maintainer_email = 'johan.vanderknijff@kb.nl',
      url = 'https://github.com/KBNLresearch/omSipCreator',
      download_url='https://github.com/KBNLresearch/omSipCreator/archive/' + find_version('omSipCreator', 'omSipCreator.py') + '.tar.gz',
      package_data={'omSipCreator': ['*.*']},
      entry_points={'console_scripts': [
        'omSipCreator = omSipCreator.omSipCreator:main',
      ]},
      classifiers=[
        'Environment :: Console',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ]
    )

