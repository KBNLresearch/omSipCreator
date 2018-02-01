#! /usr/bin/env python
"""
SIP Creator for Offline Media Images.
"""

import sys
import os
import shutil
import glob
import imp
import argparse
import codecs
import csv
import hashlib
import logging
from operator import itemgetter
from itertools import groupby
from lxml import etree
from . import config
from .mods import createMODS
from .premis import addCreationEvent
from .premis import addObjectInstance

# Bind raw_input (Python 3) to input (Python 2)
# Source: http://stackoverflow.com/a/21731110/1209004
try:
    input = raw_input
except NameError:
    pass


# Script name
config.scriptPath, config.scriptName = os.path.split(sys.argv[0])

# scriptName is empty when called from Java/Jython, so this needs a fix
if len(config.scriptName) == 0:
    config.scriptName = 'omSipCreator'

__version__ = "0.4.11"

# Create parser
parser = argparse.ArgumentParser(
    description="SIP Creator for Offline Media Images")

# Classes for Carrier and IP entries


class Carrier:
    """Carrier class"""
    def __init__(self, jobID, PPN, imagePathFull, volumeNumber, carrierType):
        """Initialise Carrier class instance"""
        self.jobID = jobID
        self.PPN = PPN
        self.imagePathFull = imagePathFull
        self.volumeNumber = volumeNumber
        self.carrierType = carrierType


class PPNGroup:
    """PPNGroup class"""
    def __init__(self):
        """initialise PPNGroup class instance"""
        self.carriers = []
        self.PPN = ""
        self.carrierType = ""

    def append(self, carrier):
        """Append a carrier. Result of this is that below PPN-level properties
        are inherited from last appended carrier (values should be identical
        for all carriers within PPN, but important to do proper QA on this as
        results may be unexpected otherwise)
        """
        self.carriers.append(carrier)
        self.PPN = carrier.PPN
        self.carrierType = carrier.carrierType


def main_is_frozen():
    """Returns True if maijn function is frozen
    (e.g. PyInstaller/Py2Exe executable)
    """
    return (hasattr(sys, "frozen") or  # new py2exe
            hasattr(sys, "importers") or  # old py2exe
            imp.is_frozen("__main__"))  # tools/freeze


def get_main_dir():
    """Reurns installation directory"""
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])


def errorExit(errors, warnings):
    """Print errors and exit"""
    logging.info("Batch verification yielded " + str(errors) +
                 " errors and " + str(warnings) + " warnings")
    sys.exit()


def checkFileExists(fileIn):
    """Check if file exists and exit if not"""
    if not os.path.isfile(fileIn):
        msg = "file " + fileIn + " does not exist!"
        sys.stderr.write("Error: " + msg + "\n")
        sys.exit()


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


def readChecksums(fileIn):
    """Read checksum file, return contents as nested list
    Also strip away any file paths if they exist (return names only)
    """

    try:
        data = []
        f = open(fileIn, "r", encoding="utf-8")
        for row in f:
            rowSplit = row.split(' ', 1)
            # Second col contains file name. Strip away any path components if they are present
            # Raises IndexError if entry only 1 col (malformed checksum file)!
            fileName = rowSplit[1].strip()
            rowSplit[1] = os.path.basename(fileName)
            data.append(rowSplit)
        f.close()
        return data
    except IOError:
        logging.fatal("cannot read '" + fileIn + "'")
        config.errors += 1
        errorExit(config.errors, config.warnings)


def generate_file_sha512(fileIn):
    """Generate sha512 hash of file
    fileIn is read in chunks to ensure it will work with (very) large files as well
    Adapted from: http://stackoverflow.com/a/1131255/1209004
    """

    blocksize = 2**20
    m = hashlib.sha512()
    with open(fileIn, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def parseCommandLine():
    """Parse command-line arguments"""

    # Sub-parsers for check and write commands

    subparsers = parser.add_subparsers(help='sub-command help',
                                       dest='subcommand')
    parser_verify = subparsers.add_parser('verify',
                                          help='only verify input batch without writing SIPs')
    parser_verify.add_argument('batchIn',
                               action="store",
                               type=str,
                               help="input batch")
    parser_prune = subparsers.add_parser('prune',
                                         help="verify input batch, then write 'pruned' version \
                         of batch that omits all PPNs that have errors. Write PPNs with \
                         errors to a separate batch.")
    parser_prune.add_argument('batchIn',
                              action="store",
                              type=str,
                              help="input batch")
    parser_prune.add_argument('batchErr',
                              action="store",
                              type=str,
                              help="name of batch that will contain all PPNs with errors")
    parser_write = subparsers.add_parser('write',
                                         help="verify input batch and write SIPs. Before using \
                         'write' first run the 'verify' command and fix any reported errors.")
    parser_write.add_argument('batchIn',
                              action="store",
                              type=str,
                              help="input batch")
    parser_write.add_argument('dirOut',
                              action="store",
                              type=str,
                              help="output directory where SIPs are written")
    parser.add_argument('--version', '-v',
                        action='version',
                        version=__version__)

    # Parse arguments
    args = parser.parse_args()

    return args


def printHelpAndExit():
    """Print usage message and exit"""
    print('')
    parser.print_help()
    sys.exit()


def processCarrier(carrier, fileGrp, SIPPath, sipFileCounterStart, counterTechMDStart):
    """Process contents of imagepath directory"""
    # TODO: * check file type / extension matches carrierType!
    # TODO: currently lots of file path manipulations which make things hard to read,
    # could be better structured with more understandable naming conventions.

    # Counters used to assign file ORDER and IDs, sipFileCounter must be unique for
    # each file within SIP

    fileCounter = 1
    sipFileCounter = sipFileCounterStart
    counterTechMD = counterTechMDStart

    # Mapping between mimeType and structmap TYPE field

    mimeTypeMap = {
        "application/x-iso9660-image": "disk image",
        "audio/flac": "audio track",
        "audio/wav": "audio track"
    }

    # Default state of flag that is set to "True" if checksums are missing
    skipChecksumVerification = False

    # All files in directory
    allFiles = glob.glob(carrier.imagePathFull + "/*")

    # Find checksum files (by extension)
    checksumFiles = [i for i in allFiles if i.endswith('.sha512')]

    # Number of checksum files must be exactly 1
    noChecksumFiles = len(checksumFiles)

    if noChecksumFiles != 1:
        logging.error("jobID " + carrier.jobID + ": found " + str(noChecksumFiles) +
                      " checksum files in directory '" +
                      carrier.imagePathFull + "', expected 1")
        config.errors += 1
        # If we end up here, checksum file either does not exist, or it is ambiguous
        # which file should be used. No point in doing the checksum verification in that case.
        skipChecksumVerification = True

    # Find logfiles and reports (by name extension)
    isobusterLogs = [i for i in allFiles if i.endswith('isobuster.log')]
    noIsobusterLogs = len(isobusterLogs)
    isobusterReports = [i for i in allFiles if i.endswith('isobuster-report.xml')]
    noIsobusterReports = len(isobusterReports)
    dBpowerampLogs = [i for i in allFiles if i.endswith('dbpoweramp.log')]
    noDbpowerampLogs = len(dBpowerampLogs)

    # Any other files (ISOs, audio files)
    otherFiles = [i for i in allFiles if not i.endswith(('.sha512', '.log'))]
    noOtherFiles = len(otherFiles)

    if noOtherFiles == 0:
        logging.error("jobID " + carrier.jobID + ": found no files in directory '" +
                      carrier.imagePathFull)
        config.errors += 1
        config.failedPPNs.append(carrier.PPN)

    # Get number of ISO files and number of audio files, and cross-check consistency
    # with log file names
    isOFiles = [i for i in otherFiles if i.endswith(('.iso', '.ISO'))]
    noIsoFiles = len(isOFiles)
    audioFiles = [i for i in otherFiles if i.endswith(
        ('.wav', '.WAV', 'flac', 'FLAC'))]
    noAudioFiles = len(audioFiles)

    if noIsoFiles > 0 and noIsobusterLogs != 1:
        logging.error("jobID " + carrier.jobID +
                      " : expected 1 file 'isobuster.log' in directory '" +
                      carrier.imagePathFull +
                      " , found " + str(noIsobusterLogs))
        config.errors += 1
        config.failedPPNs.append(carrier.PPN)

    if noIsoFiles > 0 and noIsobusterReports != 1:
        logging.error("jobID " + carrier.jobID +
                      " : expected 1 file 'isobuster-report.xml' in directory '" +
                      carrier.imagePathFull +
                      " , found " + str(noIsobusterReports))
        config.errors += 1
        config.failedPPNs.append(carrier.PPN)

    if noAudioFiles > 0 and noDbpowerampLogs != 1:
        logging.error("jobID " + carrier.jobID +
                      " : expected 1 file 'dbpoweramp.log' in directory '" +
                      carrier.imagePathFull + " , found " +
                      str(noDbpowerampLogs))
        config.errors += 1
        config.failedPPNs.append(carrier.PPN)

    if not skipChecksumVerification:
        # Read contents of checksum file to list
        checksumsFromFile = readChecksums(checksumFiles[0])

        # Sort ascending by file name - this ensures correct order when making structMap
        checksumsFromFile.sort(key=itemgetter(1))

        # List which to store names of all files that are referenced in the checksum file
        allFilesinChecksumFile = []
        for entry in checksumsFromFile:
            checksum = entry[0]
            # Raises IndexError if entry only 1 col (malformed checksum file)!
            fileName = entry[1]
            # Normalise file path relative to imagePath
            fileNameWithPath = os.path.normpath(
                carrier.imagePathFull + "/" + fileName)

            # Calculate SHA-512 hash of actual file
            checksumCalculated = generate_file_sha512(fileNameWithPath)

            if checksumCalculated != checksum:
                logging.error("jobID " + carrier.jobID + ": checksum mismatch for file '" +
                              fileNameWithPath + "'")
                config.errors += 1
                config.failedPPNs.append(carrier.PPN)

            # Get file size and append to allFilesinChecksumFile list
            # (needed later for METS file entry)
            entry.append(str(os.path.getsize(fileNameWithPath)))

            # Append file name to list
            allFilesinChecksumFile.append(fileNameWithPath)

        # Check if any files in directory are missing
        for f in otherFiles:
            if f not in allFilesinChecksumFile:
                logging.error("jobID " + carrier.jobID + ": file '" + f +
                              "' not referenced in '" +
                              checksumFiles[0] + "'")
                config.errors += 1
                config.failedPPNs.append(carrier.PPN)

        # Create METS div entry (will remain empty if createSIPs != True)
        divDiscName = etree.QName(config.mets_ns, "div")
        divDisc = etree.Element(divDiscName, nsmap=config.NSMAP)
        divDisc.attrib["TYPE"] = carrier.carrierType
        divDisc.attrib["ORDER"] = carrier.volumeNumber

        if config.createSIPs:

            # Create Volume directory
            logging.info("creating carrier directory")
            dirVolume = os.path.join(
                SIPPath, carrier.carrierType, carrier.volumeNumber)
            try:
                os.makedirs(dirVolume)
            except OSError or IOError:
                logging.fatal("jobID " + carrier.jobID +
                              ": cannot create '" + dirVolume + "'")
                config.errors += 1
                errorExit(config.errors, config.warnings)

            # Copy files to SIP Volume directory
            logging.info("copying files to carrier directory")

            # Get file names from checksum file, as this is the easiest way to make
            # post-copy checksum verification work. Filter out log files first!

            filesToCopy = [
                i for i in checksumsFromFile if not i[1].endswith(('.log', '.xml'))]

            # Set up list that will hold techMD elements
            listTechMD = []

            for entry in filesToCopy:

                checksum = entry[0]
                fileName = entry[1]
                fileSize = entry[2]
                # Generate unique file ID (used in structMap)
                fileID = "file_" + str(sipFileCounter)
                # Construct path relative to carrier directory
                fIn = os.path.join(carrier.imagePathFull, fileName)

                # Construct path relative to volume directory
                fSIP = os.path.join(dirVolume, fileName)
                try:
                    # Copy to volume dir
                    shutil.copy2(fIn, fSIP)
                except OSError:
                    logging.fatal("jobID " + carrier.jobID +
                                  ": cannot copy '" +
                                  fileName + "' to '" + fSIP + "'")
                    config.errors += 1
                    errorExit(config.errors, config.warnings)

                # Calculate hash of copied file, and verify against known value
                checksumCalculated = generate_file_sha512(fSIP)
                if checksumCalculated != checksum:
                    logging.error("jobID " + carrier.jobID + ": checksum mismatch for file '" +
                                  fSIP + "'")
                    config.errors += 1
                    config.failedPPNs.append(carrier.PPN)

                # Create METS file and FLocat elements
                fileElt = etree.SubElement(
                    fileGrp, "{%s}file" % (config.mets_ns))
                fileElt.attrib["ID"] = fileID
                fileElt.attrib["SIZE"] = fileSize
                # TODO: add SEQ and CREATED, DMDID attributes as well

                fLocat = etree.SubElement(
                    fileElt, "{%s}FLocat" % (config.mets_ns))
                fLocat.attrib["LOCTYPE"] = "URL"
                # File locations relative to SIP root (= location of METS file)
                fLocat.attrib[etree.QName(config.xlink_ns, "href")] = "file:///" + \
                    carrier.carrierType + "/" + carrier.volumeNumber + "/" + fileName

                # Add MIME type and checksum to file element
                # Note: neither of these Mimetypes are formally registered at
                # IANA but they seem to be widely used. Also, DIAS filetypes list uses /audio/x-wav!
                if fileName.endswith(".iso"):
                    mimeType = "application/x-iso9660-image"
                elif fileName.endswith(".wav"):
                    mimeType = "audio/wav"
                elif fileName.endswith(".flac"):
                    mimeType = "audio/flac"
                else:
                    mimeType = "application/octet-stream"
                fileElt.attrib["MIMETYPE"] = mimeType
                fileElt.attrib["CHECKSUM"] = checksum
                fileElt.attrib["CHECKSUMTYPE"] = "SHA-512"

                # TODO: check if mimeType values matches carrierType
                # (e.g. no audio/x-wav if cd-rom, etc.)

                # Create track divisor element for structmap
                divFile = etree.SubElement(
                    divDisc, "{%s}div" % (config.mets_ns))
                divFile.attrib["TYPE"] = mimeTypeMap[mimeType]
                divFile.attrib["ORDER"] = str(fileCounter)
                fptr = etree.SubElement(divFile, "{%s}fptr" % (config.mets_ns))
                fptr.attrib["FILEID"] = fileID

                # Create techMD element for PREMIS object information
                techMDPremisName = etree.QName(config.mets_ns, "techMD")
                techMDPremis = etree.Element(
                    techMDPremisName, nsmap=config.NSMAP)
                techMDPremisID = "techMD_" + str(counterTechMD)
                techMDPremis.attrib["ID"] = techMDPremisID

                # Add wrapper element for PREMIS object metadata
                mdWrapObjectPremis = etree.SubElement(
                    techMDPremis, "{%s}mdWrap" % (config.mets_ns))
                mdWrapObjectPremis.attrib["MIMETYPE"] = "text/xml"
                mdWrapObjectPremis.attrib["MDTYPE"] = "PREMIS:OBJECT"
                mdWrapObjectPremis.attrib["MDTYPEVERSION"] = "3.0"
                xmlDataObjectPremis = etree.SubElement(
                    mdWrapObjectPremis, "{%s}xmlData" % (config.mets_ns))

                premisObjectInfo = addObjectInstance(
                    fSIP, fileSize, mimeType, checksum)
                xmlDataObjectPremis.append(premisObjectInfo)
                listTechMD.append(techMDPremis)

                # String of techMD identifiers that are used as ADMID attribute of fileElt
                techMDIDs = techMDPremisID

                # Add techMDIDs to fileElt
                fileElt.attrib["ADMID"] = techMDIDs

                fileCounter += 1
                sipFileCounter += 1
                counterTechMD += 1

            # Generate event metadata from Isobuster/dBpoweramp logs
            # For each carrier we can have an Isobuster even, a dBpoweramp event, or both
            # Events are wrapped in a list premisEvents
            premisCreationEvents = []
            if isobusterLogs != []:
                premisEvent = addCreationEvent(isobusterLogs[0])
                premisCreationEvents.append(premisEvent)
            if dBpowerampLogs != []:
                premisEvent = addCreationEvent(dBpowerampLogs[0])
                premisCreationEvents.append(premisEvent)
        else:
            # We end up here if config.createSIPs == False
            # Dummy values (not used)
            premisCreationEvents = []
            listTechMD = []

    else:
        # We end up here if skipChecksumVerification == True
        # Dummy values (not used)
        divDisc = etree.Element('rubbish')
        premisCreationEvents = []
        listTechMD = []

    return fileGrp, divDisc, premisCreationEvents, listTechMD, sipFileCounter, counterTechMD


def processPPN(PPN, carriers, dirOut, colsBatchManifest, batchIn,
               dirsInMetaCarriers, carrierTypeAllowedValues):

    """Process a PPN"""
    # PPN is PPN identifier (by which we grouped data)
    # carriers is another iterator that contains individual carrier records

    # Create class instance for this PPN
    thisPPNGroup = PPNGroup()

    # Create METS element for this SIP
    metsName = etree.QName(config.mets_ns, "mets")
    mets = etree.Element(metsName, nsmap=config.NSMAP)
    # Add schema reference
    mets.attrib[etree.QName(config.xsi_ns, "schemaLocation")] = "".join(
        [config.metsSchema, " ", config.modsSchema, " ", config.premisSchema])
    # Subelements for dmdSec, amdSec, fileSec and structMap
    # dmdSec
    dmdSec = etree.SubElement(mets, "{%s}dmdSec" % (config.mets_ns))
    # Add identifier
    dmdSecID = "dmdSec_1"
    dmdSec.attrib["ID"] = dmdSecID
    # Create mdWrap and xmlData child elements
    mdWrapDmd = etree.SubElement(dmdSec, "{%s}mdWrap" % (config.mets_ns))
    mdWrapDmd.attrib["MDTYPE"] = "MODS"
    mdWrapDmd.attrib["MDTYPEVERSION"] = "3.4"
    xmlDataDmd = etree.SubElement(mdWrapDmd, "{%s}xmlData" % (config.mets_ns))
    # amdSec
    amdSec = etree.SubElement(mets, "{%s}amdSec" % (config.mets_ns))
    # Add identifier
    amdSecID = "amdSec_1"
    amdSec.attrib["ID"] = amdSecID

    # Create fileSec and structMap elements
    fileSec = etree.SubElement(mets, "{%s}fileSec" % (config.mets_ns))
    fileGrp = etree.SubElement(fileSec, "{%s}fileGrp" % (config.mets_ns))
    structMap = etree.SubElement(mets, "{%s}structMap" % (config.mets_ns))
    # Add top-level divisor element to structMap
    structDivTop = etree.SubElement(structMap, "{%s}div" % (config.mets_ns))
    structDivTop.attrib["TYPE"] = "physical"
    structDivTop.attrib["LABEL"] = "volumes"
    structDivTop.attrib["DMDID"] = dmdSecID

    # Initialise counters that are used to assign file and carrier-level IDs
    fileCounterStart = 1
    carrierCounterStart = 1
    carrierCounter = carrierCounterStart
    counterDigiprovMD = 1
    counterTechMD = 1

    # Dummy value for dirSIP (needed if createSIPs = False)
    dirSIP = "rubbish"

    if config.createSIPs:
        logging.info("creating SIP directory")
        # Create SIP directory
        dirSIP = os.path.join(dirOut, PPN)
        try:
            os.makedirs(dirSIP)
        except OSError:
            logging.fatal("cannot create '" + dirSIP + "'")
            config.errors += 1
            errorExit(config.errors, config.warnings)

    # Set up lists for all record fields in this PPN (needed for verifification only)
    jobIDs = []
    volumeNumbers = []
    carrierTypes = []

    # Set up list that will is used to collect all digiProv elements for all carriers within PPN
    digiProvElementsPPN = []

    # Convert to list (needed because othwerwise we can't sort)
    carriers = list(carriers)
    # Sort rows by carrier type
    carriers.sort(key=itemgetter(3))
    carriersByType = groupby(carriers, itemgetter(3))

    for carrierTypeCarriers, carrierTypeGroup in carriersByType:
        volumeNumbersTypeGroup = []
        for carrier in carrierTypeGroup:

            jobID = carrier[colsBatchManifest["jobID"]]
            volumeNumber = carrier[colsBatchManifest["volumeNo"]]
            carrierType = carrier[colsBatchManifest["carrierType"]]
            title = carrier[colsBatchManifest["title"]]
            volumeID = carrier[colsBatchManifest["volumeID"]]
            success = carrier[colsBatchManifest["success"]]
            containsAudio = carrier[colsBatchManifest["containsAudio"]]
            containsData = carrier[colsBatchManifest["containsData"]]
            cdExtra = carrier[colsBatchManifest["cdExtra"]]

            # Update jobIDs list
            jobIDs.append(jobID)

            # Check for some obvious errors

            # Check if imagePath is existing directory

            # Full path, relative to batchIn TODO: check behaviour on Window$
            imagePathFull = os.path.normpath(os.path.join(batchIn, jobID))
            imagePathAbs = os.path.abspath(imagePathFull)

            # Append absolute path to list (used later for completeness check)
            dirsInMetaCarriers.append(imagePathAbs)

            if not os.path.isdir(imagePathFull):
                logging.error("jobID " + jobID + ": '" + imagePathFull +
                              "' is not a directory")
                config.errors += 1
                config.failedPPNs.append(PPN)

            # Create Carrier class instance for this carrier
            thisCarrier = Carrier(jobID, PPN, imagePathFull,
                                  volumeNumber, carrierType)
            fileGrp, divDisc, premisEventsCarrier, listTechMD, fileCounter, counterTechMD = processCarrier(
                thisCarrier, fileGrp, dirSIP, fileCounterStart, counterTechMD)
            # NOTE
            # listTechMD: list of techMD elements, each of which represent one file.
            # Wraps EbuCore audio metdata + possibly other tech metadata
            # NOTE

            # Construct unique identifier for digiProvMD (see below) and add to divDisc as ADMID
            carrierID = "disc_" + str(carrierCounter).zfill(3)
            digiProvID = "digiprovMD_" + str(counterDigiprovMD)
            divDisc.attrib["ADMID"] = digiProvID

            # Append techMD elements to amdSec
            for techMD in listTechMD:
                amdSec.append(techMD)

            # Create digiprovMD, mdWrap and xmlData child elements

            digiprovMDName = etree.QName(config.mets_ns, "digiprovMD")
            digiprovMD = etree.Element(digiprovMDName, nsmap=config.NSMAP)
            digiprovMD.attrib["ID"] = digiProvID
            mdWrapdigiprov = etree.SubElement(
                digiprovMD, "{%s}mdWrap" % (config.mets_ns))
            mdWrapdigiprov.attrib["MIMETYPE"] = "text/xml"
            mdWrapdigiprov.attrib["MDTYPE"] = "PREMIS:EVENT"
            mdWrapdigiprov.attrib["MDTYPEVERSION"] = "3.0"
            xmlDatadigiprov = etree.SubElement(
                mdWrapdigiprov, "{%s}xmlData" % (config.mets_ns))

            # Append PREMIS events that were returned by ProcessCarrier
            for premisEvent in premisEventsCarrier:
                xmlDatadigiprov.append(premisEvent)

            digiProvElementsPPN.append(digiprovMD)

            # Add to PPNGroup class instance
            thisPPNGroup.append(thisCarrier)

            # Update fileCounterStart and counterTechMDStart
            fileCounterStart = fileCounter
            counterTechMDStart = counterTechMD

            # convert volumeNumber to integer (so we can do more checking below)
            try:
                volumeNumbersTypeGroup.append(int(volumeNumber))
            except ValueError:
                # Raises error if volumeNumber string doesn't represent integer
                logging.error("jobID " + jobID + ": '" + volumeNumber +
                              "' is illegal value for 'volumeNumber' (must be integer)")
                config.errors += 1
                config.failedPPNs.append(PPN)

            # Check carrierType value against controlled vocabulary
            if carrierType not in carrierTypeAllowedValues:
                logging.error("jobID " + jobID + ": '" + carrierType +
                              "' is illegal value for 'carrierType'")
                config.errors += 1
                config.failedPPNs.append(PPN)
            carrierTypes.append(carrierType)

            # Check success value (status)
            if success != "True":
                logging.error("jobID " + jobID +
                              ": value of 'success' not 'True'")
                config.errors += 1
                config.failedPPNs.append(PPN)

            # Check if carrierType value is consistent with containsAudio and containsData
            if carrierType in ["cd-rom", "dvd-rom", "dvd-video"] and containsData != "True":
                logging.error("jobID " + jobID + ": carrierType cannot be '" +
                              carrierType + "'if 'containsData' is 'False'")
                config.errors += 1
                config.failedPPNs.append(PPN)
            elif carrierType == "cd-audio" and containsAudio != "True":
                logging.error("jobID " + jobID + ": carrierType cannot be '" +
                              carrierType + "'if 'containsAudio' is 'False'")
                config.errors += 1
                config.failedPPNs.append(PPN)

            # Update structmap in METS
            structDivTop.append(divDisc)

            # Update counters
            carrierCounter += 1
            counterDigiprovMD += 1

        # Add volumeNumbersTypeGroup to volumeNumbers list
        volumeNumbers.append(volumeNumbersTypeGroup)

    # Get metadata of this PPN from GGC and convert to MODS format
    mdMODS = createMODS(thisPPNGroup)

    # Append metadata to METS
    xmlDataDmd.append(mdMODS)

    # Append digiProvMD elements to amdSec
    for digiProvMDElt in digiProvElementsPPN:
        amdSec.append(digiProvMDElt)

    if config.createSIPs:
        logging.info("writing METS file")

        if sys.version.startswith('3'):
            metsAsString = etree.tostring(
                mets, pretty_print=True, encoding="unicode")
        elif sys.version.startswith('2'):
            metsAsString = etree.tostring(
                mets, pretty_print=True, encoding="utf-8")

        metsFname = os.path.join(dirSIP, "mets.xml")

        with open(metsFname, "w", encoding="utf-8") as text_file:
            text_file.write(metsAsString)

    # IP-level consistency checks

    # jobID values must all be unique (no duplicates!)
    uniquejobIDs = set(jobIDs)
    if len(uniquejobIDs) != len(jobIDs):
        logging.error("PPN " + PPN + ": duplicate values found for 'jobID'")
        config.errors += 1
        config.failedPPNs.append(PPN)

    # Consistency checks on volumeNumber values within each carrierType group

    for volumeNumbersTypeGroup in volumeNumbers:
        # Volume numbers within each carrierType group must be unique
        uniqueVolumeNumbers = set(volumeNumbersTypeGroup)
        if len(uniqueVolumeNumbers) != len(volumeNumbersTypeGroup):
            logging.error("PPN " + PPN + " (" + carrierType +
                          "): duplicate values found for 'volumeNumber'")
            config.errors += 1
            config.failedPPNs.append(PPN)

        # Report warning if lower value of volumeNumber not equal to '1'
        volumeNumbersTypeGroup.sort()
        if volumeNumbersTypeGroup[0] != 1:
            logging.warning("PPN " + PPN + " (" + carrierType +
                            "): expected '1' as lower value for 'volumeNumber', found '" +
                            str(volumeNumbersTypeGroup[0]) + "'")
            config.warnings += 1

        # Report warning if volumeNumber does not contain consecutive numbers
        # (indicates either missing volumes or data entry error)

        if sorted(volumeNumbersTypeGroup) != list(range(min(volumeNumbersTypeGroup),
                                                        max(volumeNumbersTypeGroup) + 1)):
            logging.warning("PPN " + PPN + " (" + carrierType +
                            "): values for 'volumeNumber' are not consecutive")
            config.warnings += 1


def main():
    """Main CLI function"""

    # Set up logger
    logFile = "omsipcreator.log"
    # Suppress info messages from requests module
    logging.getLogger("requests").setLevel(logging.WARNING)
    logFormatter = logging.Formatter('%(levelname)s - %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)

    # Locate package directory
    packageDir = os.path.dirname(os.path.abspath(__file__))
    # Tools directory
    toolsDirUser = os.path.join(packageDir, 'tools')

    # Batch manifest file - basic capture-level metadata about carriers
    fileBatchManifest = "manifest.csv"
    fileBatchLog = "batch.log"

    # Header values of mandatory columns in batch manifest
    requiredColsBatchManifest = ['jobID',
                                 'PPN',
                                 'volumeNo',
                                 'carrierType',
                                 'title',
                                 'volumeID',
                                 'success',
                                 'containsAudio',
                                 'containsData',
                                 'cdExtra']

    # Controlled vocabulary for 'carrierType' field
    carrierTypeAllowedValues = ['cd-rom',
                                'cd-audio',
                                'dvd-rom',
                                'dvd-video']

    # Define name spaces for METS output
    config.mets_ns = 'http://www.loc.gov/METS/'
    config.mods_ns = 'http://www.loc.gov/mods/v3'
    config.premis_ns = 'http://www.loc.gov/premis/v3'
    config.ebucore_ns = 'urn:ebu:metadata-schema:ebuCore_2017'
    config.isolyzer_ns = 'https://github.com/KBNLresearch/isolyzer'
    config.xlink_ns = 'http://www.w3.org/1999/xlink'
    config.xsi_ns = 'http://www.w3.org/2001/XMLSchema-instance'
    config.metsSchema = 'http://www.loc.gov/METS/ http://www.loc.gov/standards/mets/mets.xsd'
    config.modsSchema = 'http://www.loc.gov/mods/v3 https://www.loc.gov/standards/mods/v3/mods-3-4.xsd'
    config.premisSchema = 'http://www.loc.gov/premis/v3 https://www.loc.gov/standards/premis/premis.xsd'
    config.ebucoreSchema = 'https://raw.githubusercontent.com/ebu/ebucore/master/ebucore.xsd'

    config.NSMAP = {"mets": config.mets_ns,
                    "mods": config.mods_ns,
                    "premis": config.premis_ns,
                    "ebucore": config.ebucore_ns,
                    "isolyzer": config.isolyzer_ns,
                    "xlink": config.xlink_ns,
                    "xsi": config.xsi_ns}

    # Counters for number of errors and warnings
    config.errors = 0
    config.warnings = 0

    # List of failed PPNs (used for pruning a batch)
    config.failedPPNs = []

    # Set encoding of the terminal to UTF-8
    if sys.version.startswith("2"):
        out = codecs.getwriter("UTF-8")(sys.stdout)
        err = codecs.getwriter("UTF-8")(sys.stderr)
    elif sys.version.startswith("3"):
        out = codecs.getwriter("UTF-8")(sys.stdout.buffer)
        err = codecs.getwriter("UTF-8")(sys.stderr.buffer)

    # Flag that indicates if SIPs will be written
    config.createSIPs = False

    # Flag that indicates if prune option is used
    config.pruneBatch = False

    # Get input from command line
    args = parseCommandLine()
    action = args.subcommand
    if action is None:
        # Exit and print help message if command line is empty
        printHelpAndExit()

    batchIn = os.path.normpath(args.batchIn)

    if action == "write":
        dirOut = os.path.normpath(args.dirOut)
        config.createSIPs = True
    elif action == "prune":
        batchErr = os.path.normpath(args.batchErr)
        dirOut = None
        config.pruneBatch = True
    else:
        # Dummy value
        dirOut = None

    # Path to MediaInfo
    if sys.platform is "win32":    
        config.mediaInfoExe = os.path.join(
            toolsDirUser, 'mediainfo', 'MediaInfo.exe')
    elif sys.platform in ["linux", "linux2"]:
        config.mediaInfoExe = "/usr/bin/mediainfo"
    checkFileExists(config.mediaInfoExe)

    # Check if batch dir exists
    if not os.path.isdir(batchIn):
        logging.fatal("input batch directory does not exist")
        config.errors += 1
        errorExit(config.errors, config.warnings)

    # Get listing of all directories (not files) in batch dir (used later for completeness check)
    # Note: all entries as full, absolute file paths!

    # Define dirs to ignore (jobs and jobsFailed)
    ignoreDirs = ["jobs", "jobsFailed"]

    dirsInBatch = get_immediate_subdirectories(batchIn, ignoreDirs)

    # List for storing directories as extracted from carrier metadata file (see below)
    # Note: all entries as full, absolute file paths!
    dirsInMetaCarriers = []

    # Check if batch manifest exists
    batchManifest = os.path.join(batchIn, fileBatchManifest)
    if not os.path.isfile(batchManifest):
        logging.fatal("file " + batchManifest + " does not exist")
        config.errors += 1
        errorExit(config.errors, config.warnings)

    # Read batch manifest as CSV and import header and
    # row data to 2 separate lists
    try:
        if sys.version.startswith('3'):
            # Py3: csv.reader expects file opened in text mode
            fBatchManifest = open(batchManifest, "r", encoding="utf-8")
        elif sys.version.startswith('2'):
            # Py2: csv.reader expects file opened in binary mode
            fBatchManifest = open(batchManifest, "rb")
        batchManifestCSV = csv.reader(fBatchManifest)
        headerBatchManifest = next(batchManifestCSV)
        rowsBatchManifest = [row for row in batchManifestCSV]
        fBatchManifest.close()
    except IOError:
        logging.fatal("cannot read " + batchManifest)
        config.errors += 1
        errorExit(config.errors, config.warnings)
    except csv.Error:
        logging.fatal("error parsing " + batchManifest)
        config.errors += 1
        errorExit(config.errors, config.warnings)

    # Iterate over rows and check that number of columns
    # corresponds to number of header columns.
    # Remove any empty list elements (e.g. due to EOL chars)
    # to avoid trouble with itemgetter

    colsHeader = len(headerBatchManifest)

    rowCount = 1
    for row in rowsBatchManifest:
        rowCount += 1
        colsRow = len(row)
        if colsRow == 0:
            rowsBatchManifest.remove(row)
        elif colsRow != colsHeader:
            logging.fatal("wrong number of columns in row " +
                          str(rowCount) + " of '" + batchManifest + "'")
            config.errors += 1
            errorExit(config.errors, config.warnings)

    # Create output directory if in SIP creation mode
    if config.createSIPs:
        # Remove output dir tree if it exists already
        # Potentially dangerous, so ask for user confirmation
        if os.path.isdir(dirOut):

            out.write("This will overwrite existing directory '" + dirOut +
                      "' and remove its contents!\nDo you really want to proceed (Y/N)? > ")
            response = input()

            if response.upper() == "Y":
                try:
                    shutil.rmtree(dirOut)
                except OSError:
                    logging.fatal("cannot remove '" + dirOut + "'")
                    config.errors += 1
                    errorExit(config.errors, config.warnings)

        # Create new dir
        try:
            os.makedirs(dirOut)
        except OSError:
            logging.fatal("cannot create '" + dirOut + "'")
            config.errors += 1
            errorExit(config.errors, config.warnings)

    # ********
    # ** Process batch manifest **
    # ********

    # Check that there is exactly one occurrence of each mandatory column

    for requiredCol in requiredColsBatchManifest:
        occurs = headerBatchManifest.count(requiredCol)
        if occurs != 1:
            logging.fatal("found " + str(occurs) + " occurrences of column '" +
                          requiredCol + "' in " + batchManifest + " (expected 1)")
            config.errors += 1
            # No point in continuing if we end up here ...
            errorExit(config.errors, config.warnings)

    # Set up dictionary to store header fields and corresponding column numbers
    colsBatchManifest = {}

    col = 0
    for header in headerBatchManifest:
        colsBatchManifest[header] = col
        col += 1

    # Sort rows by PPN
    rowsBatchManifest.sort(key=itemgetter(1))

    # Group by PPN
    metaCarriersByPPN = groupby(rowsBatchManifest, itemgetter(1))

    # ********
    # ** Iterate over PPNs**
    # ********

    for PPN, carriers in metaCarriersByPPN:
        logging.info("Processing PPN " + PPN)
        processPPN(PPN, carriers, dirOut, colsBatchManifest, batchIn,
                   dirsInMetaCarriers, carrierTypeAllowedValues)

    # Check if directories that are part of batch are all represented in carrier metadata file
    # (reverse already covered by checks above)

    # Diff as list
    diffDirs = list(set(dirsInBatch) - set(dirsInMetaCarriers))

    # Report each item in list as an error

    for directory in diffDirs:
        logging.error("PPN " + PPN + ": directory '" + directory +
                      "' not referenced in '" + batchManifest + "'")
        config.errors += 1
        config.failedPPNs.append(PPN)

    # Summarise no. of warnings / errors
    logging.info("Verify / write resulted in " + str(config.errors) +
                 " errors and " + str(config.warnings) + " warnings")

    # Reset warnings/errors
    config.errors = 0
    config.warnings = 0

    # Get all unique values in failedPPNs by converting to a set (and then back to a list)
    config.failedPPNs = (list(set(config.failedPPNs)))

    if config.pruneBatch and config.failedPPNs != []:

        logging.info("Start pruning")

        # Check if batchErr is an existing directory. If yes,
        # prompt user to confirm that it will be overwritten

        if os.path.isdir(batchErr):

            out.write("\nThis will overwrite existing directory '" + batchErr +
                      "' and remove its contents!\nDo you really want to proceed (Y/N)? > ")
            response = input()

            if response.upper() == "Y":
                try:
                    shutil.rmtree(batchErr)
                except OSError:
                    logging.fatal("cannot remove '" + batchErr + "'")
                    config.errors += 1
                    errorExit(config.errors, config.warnings)
            else:
                logging.error("exiting because user pressed 'N'")
                errorExit(config.errors, config.warnings)

        # Create batchErr directory

        try:
            os.makedirs(batchErr)
        except OSError or IOError:
            logging.fatal("Cannot create directory '" + batchErr + "'")
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Add batch manifest to batchErr directory
        batchManifestErr = os.path.join(batchErr, fileBatchManifest)

        # Add temporary (updated) batch manifest to batchIn
        fileBatchManifestTemp = "tmp.csv"
        batchManifestTemp = os.path.join(batchIn, fileBatchManifestTemp)

        try:
            if sys.version.startswith('3'):
                # Py3: csv.reader expects file opened in text mode
                fbatchManifestErr = open(
                    batchManifestErr, "w", encoding="utf-8")
                fbatchManifestTemp = open(
                    batchManifestTemp, "w", encoding="utf-8")
            elif sys.version.startswith('2'):
                # Py2: csv.reader expects file opened in binary mode
                fbatchManifestErr = open(batchManifestErr, "wb")
                fbatchManifestTemp = open(batchManifestTemp, "wb")
        except IOError:
            logging.fatal("cannot write batch manifest")
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Create CSV writer objects
        csvErr = csv.writer(fbatchManifestErr, lineterminator='\n')
        csvTemp = csv.writer(fbatchManifestTemp, lineterminator='\n')

        # Write header rows to batch manifests
        csvErr.writerow(headerBatchManifest)
        csvTemp.writerow(headerBatchManifest)

        # Iterate over all entries in batch manifest

        for row in rowsBatchManifest:
            jobID = row[0]
            PPN = row[1]

            if PPN in config.failedPPNs:
                # If PPN is in list of failed PPNs then add record to error batch

                # Default state of flag that is set to "True" if checksums are missing
                skipChecksumVerification = False

                # Image path for this jobID in input, pruned and error batch
                imagePathIn = os.path.normpath(os.path.join(batchIn, jobID))
                imagePathErr = os.path.normpath(os.path.join(batchErr, jobID))

                imagePathInAbs = os.path.abspath(imagePathIn)
                imagePathErrAbs = os.path.abspath(imagePathErr)

                if os.path.isdir(imagePathInAbs):

                    # Create directory in error batch
                    try:
                        os.makedirs(imagePathErrAbs)
                    except OSError or IOError:
                        logging.error("jobID " + jobID +
                                      ": could not create directory '" +
                                      imagePathErrAbs)
                        config.errors += 1

                    # All files in directory
                    allFiles = glob.glob(imagePathInAbs + "/*")

                    # Copy all files to error batch and do post-copy checksum verification
                    logging.info("Copying files to error batch")

                    for fileIn in allFiles:
                        # File base name
                        fileBaseName = os.path.basename(fileIn)

                        # Path to copied file
                        fileErr = os.path.join(imagePathErrAbs, fileBaseName)

                        # Copy file to batchErr
                        try:
                            shutil.copy2(fileIn, fileErr)
                        except IOError or OSError:
                            logging.error("jobID " + jobID + ": cannot copy '" +
                                          fileIn + "' to '" + fileErr + "'")
                            config.errors += 1

                        # Verify checksum
                        checksumIn = generate_file_sha512(fileIn)
                        checksumErr = generate_file_sha512(fileErr)

                        if checksumIn != checksumErr:
                            logging.error("jobID " + jobID + ": checksum of '" +
                                          fileIn + "' does not match '" + fileErr + "'")
                            config.errors += 1

                # Write row to error batch manifest
                logging.info("Writing batch manifest entry (batchErr)")
                csvErr.writerow(row)

                # Remove directory from input batch
                if os.path.isdir(imagePathInAbs):
                    logging.info("Removing  directory '" +
                                 imagePathInAbs + "' from batchIn")
                    try:
                        shutil.rmtree(imagePathInAbs)
                    except OSError:
                        logging.error("cannot remove '" + imagePathInAbs + "'")
                        config.errors += 1
            else:
                # Write row to temp batch manifest
                logging.info("Writing batch manifest entry (batchIn)")
                csvTemp.writerow(row)

        fbatchManifestErr.close()
        fbatchManifestTemp.close()

        # Rename original batchManifest to '.old' extension
        fileBatchManifestOld = os.path.splitext(fileBatchManifest)[0] + ".old"
        batchManifestOld = os.path.join(batchIn, fileBatchManifestOld)
        os.rename(batchManifest, batchManifestOld)

        # Rename batchManifestTemp to batchManifest
        os.rename(batchManifestTemp, batchManifest)

        logging.info("Saved old batch manifest in batchIn as '" +
                     fileBatchManifestOld + "'")

        # Copy batch log to error batch
        batchLogIn = os.path.join(batchIn, fileBatchLog)
        batchLogErr = os.path.join(batchErr, fileBatchLog)
        shutil.copy2(batchLogIn, batchLogErr)

        # Summarise no. of additional warnings / errors during pruning
        logging.info("Pruning resulted in additional " + str(config.errors) +
                     " errors and " + str(config.warnings) + " warnings")


if __name__ == "__main__":
    main()
