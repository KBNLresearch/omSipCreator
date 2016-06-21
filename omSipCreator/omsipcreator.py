#! /usr/bin/env python

import sys
import os
import argparse
import codecs
import csv
import hashlib
from operator import itemgetter
from itertools import groupby

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
* Check for presence of different carrierTypes within one identifier (not permitted)
* Check for missing checksums
* Checksum verification for all items in batch
* Check if all imagePath fields in CSV correspond to actual dir in batch
* Check if all dirs in batch are represented as an imagePath field

This validation could either be done within this SIP creator, or as a separate script.

## Code reuse

* Metamorfoze Batch converter (CSV, validation, progress and error logging)
* KB-python-API (importing of bibliographical metadata from GGC)
* For metadata generation in e.g. METS format some libs probably exist already 
* Extract + re-use metadata from ISO images, e.g. using:
     https://github.com/KBNLresearch/verifyISOSize

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

def RepresentsInt(s):
    # Check if string value represents integer
    # Source: http://stackoverflow.com/a/1267145/1209004
    try: 
        int(s)
        return True
    except ValueError:
        return False

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
    fileMetaCarriers = "metacarriers.csv"    

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
    metaCarriers = os.path.normpath(batchIn + "/" + fileMetaCarriers)
    if os.path.isfile(metaCarriers) == False:
        msg = "File " + metaCarriers + " does not exist"
        errorExit(msg)

    # Read carrier-level metadata file as CSV and import header and
    # row data to 2 separate lists
    try:
        fMetaCarriers = open(metaCarriers,"rb")
        metaCarriersCSV = csv.reader(fMetaCarriers)
        headerMetaCarriers = next(metaCarriersCSV)
        rowsMetaCarriers = [row for row in metaCarriersCSV]
        fMetaCarriers.close()
    except IOError:
        msg = "cannot read " + metaCarriers
        errorExit(msg)
    except csv.Error:
        msg = "error parsing carrier metadata CSV"
        errorExit(msg)

    # Remove any empty list elements (e.g. due to EOL chars)
    # to avoid trouble with itemgetter
    for item in rowsMetaCarriers:
        if item == []:
            rowsMetaCarriers.remove(item)

    # ********
    # ** Verification of carrier-level metadata file **
    # ******** 

    # Set up lists for storing errors and warnings
    errors = []
    warnings = []

    # Header values of mandatory columns
    requiredColsMetaCarriers = ['IPIdentifier',
                                'IPIdentifierParent',
                                'imagePath',
                                'volumeNumber',
                                'carrierType']

    # Check that there is exactly one occurrence of each mandatory column
    # TODO: bad things will happen in case of missing cols, so maybe re-introduce errorExit 
    for requiredCol in requiredColsMetaCarriers:
        occurs = headerMetaCarriers.count(requiredCol)
        if occurs != 1:
            errors.append("found " + str(occurs) + " occurrences of column " + requiredCol + " in " + fileMetaCarriers + \
            " (expected 1)")

    # Set up dictionary to store header fields and corresponding column numbers
    colsMetaCarriers = {}

    col = 0
    for header in headerMetaCarriers:
        colsMetaCarriers[header] = col
        col += 1

    # Sort rows by IPIdentifier field
    rowsMetaCarriers.sort(key=itemgetter(0))

    # Group by IPIdentifier field - creates a grouper object for each IP 
    metaCarriersByIP = groupby(rowsMetaCarriers, itemgetter(0))

    # Iterate over IPs
    for IPIdentifier, carriers in metaCarriersByIP:
        # IP is IPIdentifier (by which we grouped data)
        # carriers is another iterator that contains individual carrier records

        # TODO: perhaps we can validate PPN, based on conventions/restrictions?

        # Set up lists for all record fields in this IP (needed for verifification only)
        IPIdentifiersParent = []
        imagePaths = []
        volumeNumbers = []
        carrierTypes = []
        
        for carrier in carriers:
            # Iterate over carrier records that are part of this IP 
            IPIdentifierParent = carrier[colsMetaCarriers["IPIdentifierParent"]]
            imagePath = carrier[colsMetaCarriers["imagePath"]]
            volumeNumber = carrier[colsMetaCarriers["volumeNumber"]]
            carrierType = carrier[colsMetaCarriers["carrierType"]]

            # TODO: * validate parent PPN (see above) and/or check existence of corresponding catalog record
            #       * check for relation between IPIdentifier and IPIdentifierParent (if possible / meaningful)
            #       * check if imagePath is valid file path and/or exists
            #       * check if carrierType is part of controlled vocabulary
            #       * check imagePath against *all other* imagePath values in batch
            #       * check IPIdentifierParent against *all other* IPIdentifierParent  values in batch

            # Check for obvious errors

            # Update lists
            IPIdentifiersParent.append(IPIdentifierParent)
            imagePaths.append(imagePath)

            # convert volumeNumber to integer (so we can do more checking later)
            try:
                volumeNumbers.append(int(volumeNumber))
            except ValueError:
                # Raises error if volumeNumber string doesn't represent integer
                errors.append("IP " + IPIdentifier + ": '" + volumeNumber + \
                "' is illegal value for 'volumeNumber' (must be integer)") 
            carrierTypes.append(carrierType)
           
        # More error checking

        # Parent IP identifiers must all be equal 
        if IPIdentifiersParent.count(IPIdentifiersParent[0]) != len(IPIdentifiersParent):
            errors.append("IP " + IPIdentifier + ": multiple values found for 'IPIdentifierParent'")

        # imagePath values must all be unique (no duplicates!)
        uniqueImagePaths = set(imagePaths)
        if len(uniqueImagePaths) != len(imagePaths):
            errors.append("IP " + IPIdentifier + ": duplicate values found for 'imagePath'") 

        # Volume numbers must all be unique
        uniqueVolumeNumbers = set(volumeNumbers)
        if len(uniqueVolumeNumbers) != len(volumeNumbers):
            errors.append("IP " + IPIdentifier + ": duplicate values found for 'volumeNumber'")

        # Carrier types must all be equal 
        if carrierTypes.count(carrierTypes[0]) != len(carrierTypes):
            errors.append("IP " + IPIdentifier + ": multiple values found for 'carrierType'")

        # Report warning if lower value of volumeNumber not equal to '1'
        volumeNumbers.sort()
        if volumeNumbers[0] != 1:
            warnings.append("IP " + IPIdentifier + ": expected '1' as lower value for 'volumeNumber', found '" + \
            str(volumeNumbers[0]) + "'")
            
        # Report warning if volumeNumber does not contain consecutive numbers (indicates either missing 
        # volumes of data entry error)
        
        if sorted(volumeNumbers) != range(min(volumeNumbers), max(volumeNumbers) + 1):
            warnings.append("IP " + IPIdentifier + ": values for 'volumeNumber' are not consecutive")
            
 
          
    #print(colsMetaCarriers)
    print(errors)
    print(warnings)

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
