#!/usr/bin/env python

import codecs
import os
import re
from shutil import copytree
import sys
import site

from setuptools import setup, find_packages

def errorExit(msg):
    msgString=("Error: " + msg + "\n")
    sys.stderr.write(msgString)
    sys.exit()

def read(*parts):
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^config.__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def post_install():
    # Install pre-packaged tools to user dir
    
    from win32com.client import Dispatch
    
    # Package name
    packageName = 'omSipCreator'
        
    # Locate Windows user directory
    userDir = os.path.expanduser('~')
    # Config directory
    configDirUser = os.path.join(userDir, packageName)
    
    # Create config directory if it doesn't exist
    if os.path.isdir(configDirUser) == False:
        try:
            os.makedirs(configDirUser)
        except IOError:
            msg = 'could not create configuration directory'
            errorExit(msg)
            
    # Install tools

    # Tools directory
    toolsDirUser = os.path.join(configDirUser,'tools')
    
    if os.path.isdir(toolsDirUser) == False:
        # No tools directory in user dir, so copy it from location in source or package. Location is
        # /omsipcreator/conf/tools in 'site-packages' directory (if installed with pip)
               
        # Locate site-packages dir (this returns multiple entries)
        sitePackageDirs = site.getsitepackages()
        
        # Assumptions: site package dir is called 'site-packages' and is unique (?)
        for dir in sitePackageDirs:
            if 'site-packages'in dir:
                sitePackageDir = dir
                
        # Construct path to tools dir
        toolsDirPackage = os.path.join(sitePackageDir, packageName, 'tools')
        
        # If package tools dir exists, copy it to the user directory        
        if os.path.isdir(toolsDirPackage) == True:
            try:
                copytree(toolsDirPackage, toolsDirUser)
            except IOError:
                msg = 'could not copy tools directory to ' + toolsDirUser
                errorExit(msg)
        # This should never happen but who knows ...
        else:
            msg = 'no tools directory found in package'
            errorExit(msg)
     
    
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
      install_requires=install_requires,
      platforms=['POSIX', 'Windows'],
      description='Create ingest-ready SIPs from batches of optical media images',
      long_description='Create ingest-ready SIPs from batches of optical media images',
      author='Johan van der Knijff',
      author_email='johan.vanderknijff@kb.nl',
      maintainer='Johan van der Knijff',
      maintainer_email = 'johan.vanderknijff@kb.nl',
      url = 'https://github.com/KBNLresearch/omSipCreator',
      download_url='https://github.com/KBNLresearch/omSipCreator/archive/' + find_version('omSipCreator', 'omSipCreator.py') + '.tar.gz',
      package_data={'omSipCreator': ['*.*','tools/*.*','tools/mediainfo/*.*','tools/mediainfo/Plugin/*.*','tools/mediainfo/Plugin/Custom/*.*']},
      zip_safe=False,
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

if sys.argv[1] == 'install' and sys.platform == 'win32':
    post_install()
