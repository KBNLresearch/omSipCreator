#! /usr/bin/env python

"""
Various shared functions
"""

import os
import sys
import subprocess as sub
import string
import logging
from random import choice
from lxml import etree
from . import byteconv as bc


def errorExit(errors, warnings):
    """Print errors and exit"""
    logging.info("Batch verification yielded " + str(errors) +
                 " errors and " + str(warnings) + " warnings")
    sys.exit()


def makeHumanReadable(element, remapTable={}):
    """Takes element object, and returns a modified version in which all
    non-printable 'text' fields (which may contain numeric data or binary strings)
    are replaced by printable strings
    Property values in original tree may be mapped to alternative (more user-friendly)
    reportable values using a remapTable, which is a nested dictionary.
    TODO: add to separate module
    """

    for elt in element.iter():
        # Text field of this element
        textIn = elt.text

        # Tag name
        tag = elt.tag

        # Step 1: replace property values by values defined in enumerationsMap,
        # if applicable
        try:
            # If tag is in enumerationsMap, replace property values
            parameterMap = remapTable[tag]
            try:
                # Map original property values to values in dictionary
                remappedValue = parameterMap[textIn]
            except KeyError:
                # If value doesn't match any key: use original value
                # instead
                remappedValue = textIn
        except KeyError:
            # If tag doesn't match any key in enumerationsMap, use original
            # value
            remappedValue = textIn

        # Step 2: convert all values to text strings.

        # First set up list of all numeric data types,
        # which is dependent on the Python version used

        if sys.version.startswith("2"):
            # Python 2.x
            numericTypes = [int, long, float, bool]
            # Long type is deprecated in Python 3.x!
        else:
            numericTypes = [int, float, bool]

        # Convert

        if remappedValue is not None:
            # Data type
            textType = type(remappedValue)

            # Convert text field, depending on type
            if textType == bytes:
                textOut = bc.bytesToText(remappedValue)
            elif textType in numericTypes:
                textOut = str(remappedValue)
            else:
                # Remove control chars and strip leading/ trailing whitespaces
                textOut = bc.removeControlCharacters(remappedValue).strip()

            # Update output tree
            elt.text = textOut


def add_ns_prefix(tree, ns):
    """Iterates over element tree and adds prefix to all elements
    Adapted from https://stackoverflow.com/a/30233635/1209004
    """
    # Iterate through only element nodes (skip comment node, text node, etc) :
    for element in tree.xpath('descendant-or-self::*'):
        # if element has no prefix...
        if not element.prefix:
            tagIn = etree.QName(element).localname
            tagOut = "{" + ns + "}" + tagIn
            element.tag = tagOut
    return tree


def launchSubProcess(args):
    """Launch subprocess and return exit code, stdout and stderr"""
    try:
        # Execute command line; stdout + stderr redirected to objects
        # 'output' and 'errors'.
        p = sub.Popen(args, stdout=sub.PIPE, stderr=sub.PIPE, shell=False)
        output, errors = p.communicate()

        # Decode to UTF8
        outputAsString = output.decode('utf-8')
        errorsAsString = errors.decode('utf-8')

        exitStatus = p.returncode

    except Exception:
        # I don't even want to to start thinking how one might end up here ...

        exitStatus = -99
        outputAsString = ""
        errorsAsString = ""

    return(exitStatus, outputAsString, errorsAsString)


def get_immediate_subdirectories(a_dir, ignoreDirs):
    """Returns list of immediate subdirectories
    Directories that end with suffixes defined by ignoreDirs are ignored
    """
    subDirs = []
    for root, dirs, files in os.walk(a_dir):
        for myDir in dirs:
            ignore = False
            for ignoreDir in ignoreDirs:
                if myDir.endswith(ignoreDir):
                    ignore = True
            if not ignore:
                subDirs.append(os.path.abspath(os.path.join(root, myDir)))

    return subDirs


def randomString(length):
    """Generate text string with random characters (a-z;A-Z;0-9)"""
    return ''.join(choice(string.ascii_letters + string.digits) for i in range(length))


def index_startswith_substring(the_list, substring):
    """Return index of element in the_list that starts with substring,
    and -1 if substring was not found
    """
    for i, s in enumerate(the_list):
        if s.startswith(substring):
            return i
    return -1


class cd:
    """Context manager for changing the current working directory
    Source: http://stackoverflow.com/a/13197763
    """

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)
