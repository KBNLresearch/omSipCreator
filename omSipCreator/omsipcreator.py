#! /usr/bin/env python

import sys
import os
import argparse
import codecs
import csv
import hashlib

# For checksumming, check this:
# http://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file


# Script name
scriptPath, scriptName = os.path.split(sys.argv[0])

# scriptName is empty when called from Java/Jython, so this needs a fix
if len(scriptName) == 0:
    scriptName = 'omsipcreator'

__version__ = "0.1.0"

# Create parser
parser = argparse.ArgumentParser(
    description="SIP creation tool for optical media images")

def main_is_frozen():
    return (hasattr(sys, "frozen") or  # new py2exe
            hasattr(sys, "importers")  # old py2exe
            or imp.is_frozen("__main__"))  # tools/freeze

def get_main_dir():
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])

def printWarning(msg):
    msgString=("User warning: " + msg +"\n")
    sys.stderr.write(msgString)

def printInfo(msg):
    msgString=(msg + "\n")
    sys.stderr.write(msgString)
 
def errorExit(msg):
    msgString=("Error: " + msg + "\n")
    sys.stderr.write(msgString)
    sys.exit()

def parseCommandLine():
    # Add arguments

    parser.add_argument('batchIn',
                        action="store",
                        type=str,
                        help="input batch")
    parser.add_argument('dirOut',
                        action="store",
                        type=str,
                        help="output directory")

    # Parse arguments
    args = parser.parse_args()

    return(args)

def main():
    # Get input from command line
    args = parseCommandLine()
    batchIn = os.path.normpath(args.batchIn)
    dirOut = os.path.normpath(args.dirOut)

    if os.path.isdir(batchIn) == False:
        msg = "input batch directory does not exist"
        errorExit(msg)

    # Create output dir if it doesn't exist already
    if os.path.isdir(dirOut) == False:
        try:
            os.makedirs(dirOut)
        except IOError:
            msg = "cannot create output directory"
            errorExit(msg)


    print(batchIn + " " + dirOut)

if __name__ == "__main__":
    main()
