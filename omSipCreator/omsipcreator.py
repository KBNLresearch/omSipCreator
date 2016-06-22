#! /usr/bin/env python

import sys
import os
import glob
import argparse
import codecs
import csv
import hashlib
from operator import itemgetter
from itertools import groupby

"""
NOTES
-----

## SIP structure

Current code based on multi-volume SIPS. But OAIS allow one to describe a composite object as an
Archival Information Collection (AIC). This may be a better solution, which would imply 
single-volume SIPs. See also:

http://qanda.digipres.org/1121/creation-practices-optical-carriers-that-multiple-volumes

## Metadata

LoC has a METS profile for audio CDs:

<http://www.loc.gov/standards/mets/profiles/00000007.html>

## Checksumming

Check out this:  

<http://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file>

## Batch validation

Before doing ANYTHING, we'll also need to do some basic validation at 
the batch level, e.g.:

* Check for duplicate identifier - volumeNumber combinations (not permitted) X
* Check for presence of different carrierTypes within one identifier (not permitted) X
* Check for missing checksums X
* Checksum verification for all items in batch X
* Check if all imagePath fields in CSV correspond to actual dir in batch X
* Check if all dirs in batch are represented as an imagePath field X

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
 
def errorExit(errors,terminal):
    for error in errors:
        terminal.write("Error - " + error + "\n")
    sys.exit()
    
def get_immediate_subdirectories(a_dir):
    subDirs = []
    for root, dirs, files in os.walk(a_dir):
        for dir in dirs:
            subDirs.append(os.path.join(root, dir))

    return(subDirs)

def readMD5(fileIn):
    # Read MD 5 file, return contents as nested list

    try:
        data = []
        f = open(fileIn,"r")
        for row in f:
            rowSplit = row.split()
            data.append(rowSplit)    
        f.close()
        return(data)
    except IOError:
        errors.append("cannot read '" + fileIn + "'")
        errorExit(errors,err)

def generate_file_md5(fileIn):
    # Generate MD5 hash of file
    # fileIn is read in chunks to ensure it will work with (very) large files as well
    # Adapted from: http://stackoverflow.com/a/1131255/1209004

    blocksize = 2**20
    m = hashlib.md5()
    with open(fileIn, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()
     
def processImagePath(IPIdentifier, imagePathFull):
    # Process contents of imagepath directory
    # TODO: * check file type / extension matches carrierType!
    
    skipChecksumVerification = False
    
    # All files in directory
    allFiles = glob.glob(imagePathFull + "/*")
    
    # Find MD5 files (by extension)
    MD5Files = [i for i in allFiles if i.endswith('.md5')]
      
    # Number of MD5 files must be exactly 1
    noMD5Files = len(MD5Files)
    
    if noMD5Files != 1:
        errors.append("IP " + IPIdentifier + ": found " + str(noMD5Files) + " '.md5' files in directory '" \
        + imagePathFull + "', expected 1")
        # If we end up here, checksum file either does not exist, or it is ambiguous 
        # which file should be used. No point in doing the checksum verification in that case.  
        skipChecksumVerification = True

    # Any other files (ISOs, audio files)
    otherFiles = [i for i in allFiles if not i.endswith('.md5')]
    noOtherFiles = len(otherFiles)
    
    if skipChecksumVerification == False:
        MD5FromFile = readMD5(MD5Files[0])
        
        # List which to store names of all files that are referenced in the MD5 file
        allFilesinMD5 = []
        for entry in MD5FromFile:
            md5Sum = entry[0]
            fileName = entry[1] # Raises IndexError if entry only 1 col (malformed MD5 file)!
            fileNameWithPath = os.path.normpath(imagePathFull + "/" + fileName)
            
            # Calculate MD5 hash of actual file
            md5SumCalculated = generate_file_md5(fileNameWithPath)
                                   
            if md5SumCalculated != md5Sum:
                errors.append("IP " + IPIdentifier + ": checksum mismatch for file '" + fileNameWithPath + "'")
                        
            # Append file name to list 
            allFilesinMD5.append(fileNameWithPath)
            
        # Check if any files in directory are missing from MD5 file
        for f in otherFiles:
            if f not in allFilesinMD5:
                errors.append("IP " + IPIdentifier + ": file '" + f + "' not referenced in '" + \
                MD5Files[0] + "'")           
    
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
    
    # Flag that indicates (batch) validation-only mode or SIP-creation mode
    createSIPs = True
    
    # Carrier metadata file - basic capture-level metadata about carriers
    fileMetaCarriers = "metacarriers.csv"

    # Header values of mandatory columns in carrier metadata file
    requiredColsMetaCarriers = ['IPIdentifier',
                                'IPIdentifierParent',
                                'imagePath',
                                'volumeNumber',
                                'carrierType']
    
    # Controlled vocabulary for 'carrierType' field
    carrierTypeAllowedValues = ['cd-rom',
                                'cd-audio',
                                'dvd-rom',
                                'dvd-video']
    
    # Set up lists for storing errors and warnings
    # Defined as global so we can easily add to them within functions
    global errors
    global warnings
    errors = []
    warnings = []
    
    # Set encoding of the terminal to UTF-8
    if sys.version.startswith("2"):
        out = codecs.getwriter("UTF-8")(sys.stdout)
        err = codecs.getwriter("UTF-8")(sys.stderr)
    elif sys.version.startswith("3"):
        out = codecs.getwriter("UTF-8")(sys.stdout.buffer)
        err = codecs.getwriter("UTF-8")(sys.stderr.buffer)
       
    # Get input from command line
    args = parseCommandLine()
    batchIn = os.path.normpath(args.batchIn)
    dirOut = os.path.normpath(args.dirOut)

    # Check if batch dir exists
    if os.path.isdir(batchIn) == False:
        errors.append("input batch directory does not exist")
        errorExit(errors,err)
        
    # Get listing of all directories (not files) in batch dir (used later for completeness check)
    # Note: all entries as full, absolute file paths!
    dirsInBatch = get_immediate_subdirectories(batchIn)
    
    # List for storing directories as extracted from carrier metadata file (see below)
    # Note: all entries as full, absolute file paths!
    dirsInMetaCarriers = [] 
    
    # Check if batch-level carrier metadata file exists
    metaCarriers = os.path.normpath(batchIn + "/" + fileMetaCarriers)
    if os.path.isfile(metaCarriers) == False:
        errors.append("file " + metaCarriers + " does not exist")
        errorExit(errors,err)

    # Read carrier-level metadata file as CSV and import header and
    # row data to 2 separate lists
    # TODO: make this work in Python 3, see also:
    # http://stackoverflow.com/a/5181085/1209004
    try:
        fMetaCarriers = open(metaCarriers,"rb")
        metaCarriersCSV = csv.reader(fMetaCarriers)
        headerMetaCarriers = next(metaCarriersCSV)
        rowsMetaCarriers = [row for row in metaCarriersCSV]
        fMetaCarriers.close()
    except IOError:
        errors.append("cannot read " + metaCarriers)
        errorExit(errors,err)
    except csv.Error:
        errors.append("error parsing " + metaCarriers)
        errorExit(errors,err)

    # Remove any empty list elements (e.g. due to EOL chars)
    # to avoid trouble with itemgetter
    for item in rowsMetaCarriers:
        if item == []:
            rowsMetaCarriers.remove(item)

    # ********
    # ** Process carrier-level metadata file **
    # ******** 

    # Check that there is exactly one occurrence of each mandatory column
 
    for requiredCol in requiredColsMetaCarriers:
        occurs = headerMetaCarriers.count(requiredCol)
        if occurs != 1:
            errors.append("found " + str(occurs) + " occurrences of column '" + requiredCol + "' in " + \
            fileMetaCarriers + " (expected 1)")
            # No point in continuing if we end up here ...
            errorExit(errors,err)

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
            #       * check imagePath against *all other* imagePath values in batch
            #       * check IPIdentifierParent against *all other* IPIdentifierParent  values in batch

            # Update lists and check for some obvious errors
                      
            IPIdentifiersParent.append(IPIdentifierParent)
            imagePaths.append(imagePath)
            
            # Check if imagePath is existing directory
            
            # Full path, relative to batchIn TODO: check behaviour on Window$
            imagePathFull = os.path.normpath(os.path.join(batchIn, imagePath)) 
            imagePathAbs = os.path.abspath(imagePathFull)
            
            # Append absolute path to list (used later for completeness check)
            dirsInMetaCarriers.append(imagePathAbs)
            
            if os.path.isdir(imagePathFull) == False:
                errors.append("IP " + IPIdentifier + ": '" + imagePath + \
                "' is not a directory")
            
            # Process contents of imagePath directory
            processImagePath(IPIdentifier,imagePathFull)
            
            # convert volumeNumber to integer (so we can do more checking below)
            try:
                volumeNumbers.append(int(volumeNumber))
            except ValueError:
                # Raises error if volumeNumber string doesn't represent integer
                errors.append("IP " + IPIdentifier + ": '" + volumeNumber + \
                "' is illegal value for 'volumeNumber' (must be integer)") 

            # Check carrierType value against controlled vocabulary 
            if carrierType not in carrierTypeAllowedValues:
                errors.append("IP " + IPIdentifier + ": '" + carrierType + \
                "' is illegal value for 'carrierType'")
            carrierTypes.append(carrierType)
                   
        # IP-level consistency checks

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
        # volumes or data entry error)
        
        if sorted(volumeNumbers) != range(min(volumeNumbers), max(volumeNumbers) + 1):
            warnings.append("IP " + IPIdentifier + ": values for 'volumeNumber' are not consecutive")
    
    # Check if directories that are part of batch are all represented in carrier metadata file
    # (reverse already covered by checks above)
    
    # Diff as list
    diffDirs = list(set(dirsInBatch) - set(dirsInMetaCarriers))
    
    # Report each item in list as an error
    
    for directory in diffDirs:
        errors.append("IP " + IPIdentifier + ": directory '" + directory + "' not referenced in '"\
        + metaCarriers + "'")
 
    # Print errors and warnings
    err.write("Batch validation yielded " + str(len(errors)) + " errors and " + str(len(warnings)) + " warnings \n" )
    
    for error in errors:
        err.write("Error - " + error + "\n")
        
    for warning in warnings:
        err.write("Warning - " + warning + "\n") 
 
    #print(errors)
    #print(warnings)

    """
    # Create output dir if it doesn't exist already
    if os.path.isdir(dirOut) == False:
        try:
            os.makedirs(dirOut)
        except IOError:
            msg = "cannot create output directory"
            errorExit(errors)
    """


if __name__ == "__main__":
    main()
