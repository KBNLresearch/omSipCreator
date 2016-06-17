#! /usr/bin/env python

import sys
import os
import argparse
import codecs
import csv
import hashlib

"""
NOTES
-----

## Checksumming

Check out this:  

<http://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file>

## Batch validation

Before doing ANYTHING, we'll also need to do some basic validation at 
the batch level, e.g.:

* Check for duplicate identifier - volumeNumber combinations (not permitted)
* Check for presence of different carrierTypes within one identifier (no permitted)
* Check for missing checksums
* Checksum verification for all items in batch
* Check if all imagePath fields in CSV correspond to actual dir in batch
* Check if all dirs in batch are represented as an imagePath field

This validation could either be done within this SIP creator, or as a separate script.

## Code reuse

* Metamorfoze Batch converter (CSV, validation, progress and error logging)
* KB-python-API (importing of bibliographical metadata from GGC)
* For metadata generation in e.g. METS format some libs probably exist already 

"""


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

def getColumnNumber(CSVHeader, matchString):
    # Search for matchString in CSVHeader and return 
    # column number (first occurrence)
    # Also check number of occurrences of matchString, and exit
    # if greater than 1
    try:
        col = CSVHeader.index(matchString)
        occurs = CSVHeader.count(matchString)

        if occurs > 1:
            msg = "found more than 1 occurrence of column " + matchString
            errorExit(msg)
        return(col)
    except ValueError:
        msg = "column " + matchString + " missing in CSV file"
        errorExit(msg)

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

    # Constants (put in config file later)
    fileMetaBatch = "metabatch.csv"    

    # Get input from command line
    args = parseCommandLine()
    batchIn = os.path.normpath(args.batchIn)
    dirOut = os.path.normpath(args.dirOut)

    # TODO: perhaps the checks below (which now all result in an errorexit)
    # could be formalised a bit, so that they can be reworked into a validation
    # report. 

    # Check if batch dir exists
    if os.path.isdir(batchIn) == False:
        msg = "input batch directory does not exist"
        errorExit(msg)

    # Check if batch-level metadata file exists
    metaBatch = os.path.normpath(batchIn + "/" + fileMetaBatch)
    if os.path.isfile(metaBatch) == False:
        msg = "File " + metaBatch + " does not exist"
        errorExit(msg)

    # Read batch-level metadata file as CSV and import to list
    try:
        fMetaBatch = open(metaBatch,"rb")
        metaBatchCSV = csv.reader(fMetaBatch)
        lMetaBatch = list(metaBatchCSV)
        fMetaBatch.close()
    except IOError:
        msg = "cannot read " + metaBatch
        errorExit(msg)
    except csv.Error:
        msg = "error parsing CSV"
        errorExit(msg)

    # Find column positions of metadata fields, based on header row
    # If any columns are missing, SIP creator will exit with error message
    colIPIdentifier = getColumnNumber(lMetaBatch[0], "IPIdentifier")
    colIPIdentifierParent = getColumnNumber(lMetaBatch[0], "IPIdentifierParent")
    colImagePath = getColumnNumber(lMetaBatch[0],"imagePath")
    colVolumeNumber = getColumnNumber(lMetaBatch[0],"volumeNumber")
    colCarrierType = getColumnNumber(lMetaBatch[0],"carrierType")
    
    print(colIPIdentifier, colIPIdentifierParent, colImagePath, colVolumeNumber, colCarrierType)

    """
    # Create output dir if it doesn't exist already
    if os.path.isdir(dirOut) == False:
        try:
            os.makedirs(dirOut)
        except IOError:
            msg = "cannot create output directory"
            errorExit(msg)
    """


if __name__ == "__main__":
    main()
