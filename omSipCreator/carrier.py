#! /usr/bin/env python
"""
Processing functions for one carrier
"""

import os
import shutil
import glob
import logging
from operator import itemgetter
from lxml import etree
from . import config
from . import checksums
from .shared import errorExit
from .cdinfo import parseCDInfoLog
from .premis import addCreationEvent
from .premis import addObjectInstance


def processCarrier(carrier, SIPPath, sipFileCounterStart, counterTechMDStart):
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
    cdinfoLogs = [i for i in allFiles if i.endswith('cd-info.log')]
    noCdinfoLogs = len(cdinfoLogs)
    isobusterLogs = [i for i in allFiles if i.endswith('isobuster.log')]
    noIsobusterLogs = len(isobusterLogs)
    isobusterReports = [i for i in allFiles if i.endswith('isobuster-report.xml')]
    noIsobusterReports = len(isobusterReports)
    dBpowerampLogs = [i for i in allFiles if i.endswith('dbpoweramp.log')]
    noDbpowerampLogs = len(dBpowerampLogs)

    # Any other files (ISOs, audio files)
    otherFiles = [i for i in allFiles if not i.endswith(('.sha512', '.log'))]
    noOtherFiles = len(otherFiles)

    if noCdinfoLogs != 1:
        logging.error("jobID " + carrier.jobID +
                      " : expected 1 file 'cd-info.log' in directory '" +
                      carrier.imagePathFull +
                      " , found " + str(noCdinfoLogs))
        config.errors += 1
        config.failedPPNs.append(carrier.PPN)

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
        checksumsFromFile = checksums.readChecksums(checksumFiles[0])

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
            if os.path.isfile(fileNameWithPath):
                checksumCalculated = checksums.generate_file_sha512(fileNameWithPath)
            else:
                logging.fatal("jobID " + carrier.jobID + ": file '" +
                              fileNameWithPath + "' is referenced in '" + checksumFiles[0] +
                              "', but does not exist")
                config.errors += 1
                config.failedPPNs.append(carrier.PPN)
                errorExit(config.errors, config.warnings)

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

        # Representation-level tech metadata from cd-info.log
        if cdinfoLogs != []:
            cdInfoElt, dataSectorOffset = parseCDInfoLog(cdinfoLogs[0])
        else:
            # Create empty cd-info element
            cdInfoName = etree.QName(config.cdInfo_ns, "cd-info")
            cdInfoElt = etree.Element(
                cdInfoName, nsmap=config.NSMAP)
            dataSectorOffset = 0

        # Metadata from Isobuster report (return empy element in case of parse
        # errors)
        if isobusterReports != []:
            try:
                isobusterReportElt = etree.parse(isobusterReports[0]).getroot()
            except:
                logging.error("jobID " + carrier.jobID +
                              ": error parsing '" + isobusterReports[0] + "'")
                config.errors += 1
                isobusterReportElt = etree.Element("dfxml")
        else:
            isobusterReportElt = etree.Element("dfxml")

        if config.createSIPs:

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

            # Create Volume directory
            logging.info("creating carrier directory")
            dirVolume = os.path.join(
                SIPPath, carrier.carrierType, carrier.volumeNumber)
            try:
                os.makedirs(dirVolume)
            except (OSError, IOError):
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

            # Set up list that will hold file elements and file-level 
            # techMD elements
            fileElements = []
            techMDFileElements = []

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
                checksumCalculated = checksums.generate_file_sha512(fSIP)
                if checksumCalculated != checksum:
                    logging.error("jobID " + carrier.jobID + ": checksum mismatch for file '" +
                                  fSIP + "'")
                    config.errors += 1
                    config.failedPPNs.append(carrier.PPN)

                # Create METS file and FLocat elements

                fileEltName = etree.QName(config.mets_ns, "file")
                fileElt = etree.Element(
                    fileEltName, nsmap=config.NSMAP)

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
                    fSIP, fileSize, mimeType, checksum, dataSectorOffset, isobusterReportElt)
                xmlDataObjectPremis.append(premisObjectInfo)
                techMDFileElements.append(techMDPremis)

                # String of techMD identifiers that are used as ADMID attribute of fileElt
                techMDIDs = techMDPremisID

                # Add techMDIDs to fileElt
                fileElt.attrib["ADMID"] = techMDIDs

                # Add fileElt to fileElements
                fileElements.append(fileElt)

                fileCounter += 1
                sipFileCounter += 1
                counterTechMD += 1

        else:
            # We end up here if config.createSIPs == False
            # Dummy values (not used)
            premisCreationEvents = []
            fileElements = []
            techMDFileElements = []

    else:
        # We end up here if skipChecksumVerification == True
        # Dummy values (not used)
        divDisc = etree.Element('rubbish')
        premisCreationEvents = []
        fileElements = []
        techMDFileElements = []

    # Wrap all output in dictionary
    carrierOut = {}
    carrierOut['divDisc'] = divDisc
    carrierOut['fileElements'] = fileElements
    carrierOut['techMDFileElements'] = techMDFileElements
    carrierOut['premisCreationEvents'] = premisCreationEvents
    carrierOut['cdInfoElt'] = cdInfoElt
    carrierOut['sipFileCounter'] = sipFileCounter
    carrierOut['counterTechMD'] = counterTechMD

    return carrierOut
