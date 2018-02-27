#! /usr/bin/env python
"""
Class and processing functions for one carrier
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


class Carrier:
    """Carrier class"""
    def __init__(self, jobID, PPN, imagePathFull, volumeNumber, carrierType):
        """Initialise Carrier class instance"""
        self.jobID = jobID
        self.PPN = PPN
        self.imagePathFull = imagePathFull
        self.volumeNumber = volumeNumber
        self.carrierType = carrierType
        self.divFileElements = []
        self.fileElements = []
        self.techMDFileElements = []
        self.premisCreationEvents = []
        cdInfoName = etree.QName(config.cdInfo_ns, "cd-info")
        self.cdInfoElt = etree.Element(cdInfoName, nsmap=config.NSMAP)

    def process(self, SIPPath, sipFileCounterStart, counterTechMDStart):
        """Process one carrier"""
        # TODO: * check file type / extension matches carrierType!
        # TODO: currently lots of file path manipulations which make things hard to read,
        # could be better structured with more understandable naming conventions.

        fileCounter = 1
        sipFileCounter = sipFileCounterStart
        counterTechMD = counterTechMDStart

        # Mapping between mimeType and structmap TYPE field

        mimeTypeMap = {
            "application/x-iso9660-image": "disk image",
            "audio/flac": "audio track",
            "audio/wav": "audio track"
        }

        # All files in directory
        allFiles = glob.glob(self.imagePathFull + "/*")

        # Find checksum files (by extension)
        checksumFiles = [i for i in allFiles if i.endswith('.sha512')]

        # Number of checksum files must be exactly 1
        noChecksumFiles = len(checksumFiles)

        if noChecksumFiles != 1:
            logging.fatal("jobID " + self.jobID + ": found " + str(noChecksumFiles) +
                          " checksum files in directory '" +
                          self.imagePathFull + "', expected 1")

            config.errors += 1
            config.failedPPNs.append(self.PPN)
            errorExit(config.errors, config.warnings)


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
            logging.error("jobID " + self.jobID +
                          " : expected 1 file 'cd-info.log' in directory '" +
                          self.imagePathFull +
                          " , found " + str(noCdinfoLogs))
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        if noOtherFiles == 0:
            logging.error("jobID " + self.jobID + ": found no files in directory '" +
                          self.imagePathFull)
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Get number of ISO files and number of audio files, and cross-check consistency
        # with log file names
        isOFiles = [i for i in otherFiles if i.endswith(('.iso', '.ISO'))]
        noIsoFiles = len(isOFiles)
        audioFiles = [i for i in otherFiles if i.endswith(
            ('.wav', '.WAV', 'flac', 'FLAC'))]
        noAudioFiles = len(audioFiles)

        if noIsoFiles > 0 and noIsobusterLogs != 1:
            logging.error("jobID " + self.jobID +
                          " : expected 1 file 'isobuster.log' in directory '" +
                          self.imagePathFull +
                          " , found " + str(noIsobusterLogs))
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        if noIsoFiles > 0 and noIsobusterReports != 1:
            logging.error("jobID " + self.jobID +
                          " : expected 1 file 'isobuster-report.xml' in directory '" +
                          self.imagePathFull +
                          " , found " + str(noIsobusterReports))
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        if noAudioFiles > 0 and noDbpowerampLogs != 1:
            logging.error("jobID " + self.jobID +
                          " : expected 1 file 'dbpoweramp.log' in directory '" +
                          self.imagePathFull + " , found " +
                          str(noDbpowerampLogs))
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Read contents of checksum file to list
        checksumsFromFile = checksums.readChecksums(checksumFiles[0])

        # Sort ascending by file name - this ensures correct order when making structMap
        checksumsFromFile.sort(key=itemgetter(1))

        # List to store names of all files that are referenced in the checksum file
        allFilesinChecksumFile = []
        for entry in checksumsFromFile:
            checksum = entry[0]
            # Raises IndexError if entry only 1 col (malformed checksum file)!
            fileName = entry[1]
            # Normalise file path relative to imagePath
            fileNameWithPath = os.path.normpath(
                self.imagePathFull + "/" + fileName)

            # Calculate SHA-512 hash of actual file
            if os.path.isfile(fileNameWithPath) and config.skipChecksumFlag == False:
                checksumCalculated = checksums.generate_file_sha512(fileNameWithPath)
            elif os.path.isfile(fileNameWithPath) and config.skipChecksumFlag == True:
                checksumCalculated = "bogus"
            else:
                logging.fatal("jobID " + self.jobID + ": file '" +
                              fileNameWithPath + "' is referenced in '" + checksumFiles[0] +
                              "', but does not exist")
                config.errors += 1
                config.failedPPNs.append(self.PPN)
                errorExit(config.errors, config.warnings)

            if checksumCalculated != checksum and config.skipChecksumFlag == False:
                logging.error("jobID " + self.jobID + ": checksum mismatch for file '" +
                              fileNameWithPath + "'")
                config.errors += 1
                config.failedPPNs.append(self.PPN)

            # Get file size and append to allFilesinChecksumFile list
            # (needed later for METS file entry)
            entry.append(str(os.path.getsize(fileNameWithPath)))

            # Append file name to list
            allFilesinChecksumFile.append(fileNameWithPath)

        # Check if any files in directory are missing
        for f in otherFiles:
            if f not in allFilesinChecksumFile:
                logging.error("jobID " + self.jobID + ": file '" + f +
                              "' not referenced in '" +
                              checksumFiles[0] + "'")
                config.errors += 1
                config.failedPPNs.append(self.PPN)

        # Carrier-level (representation) tech metadata from cd-info.log
        if cdinfoLogs != []:
            self.cdInfoElt, dataSectorOffset = parseCDInfoLog(cdinfoLogs[0])
        else:
            dataSectorOffset = 0

        # Metadata from Isobuster report (return empy element in case of parse
        # errors)
        if isobusterReports != []:
            try:
                isobusterReportElt = etree.parse(isobusterReports[0]).getroot()
            except:
                logging.error("jobID " + self.jobID +
                              ": error parsing '" + isobusterReports[0] + "'")
                config.errors += 1
                isobusterReportElt = etree.Element("dfxml")
        else:
            isobusterReportElt = etree.Element("dfxml")

        if config.createSIPs:

            # Generate event metadata from Isobuster/dBpoweramp logs
            # For each carrier we can have an Isobuster even, a dBpoweramp event, or both
            # Events are wrapped in a list premisEvents
            if isobusterLogs != []:
                premisEvent = addCreationEvent(isobusterLogs[0])
                self.premisCreationEvents.append(premisEvent)
            if dBpowerampLogs != []:
                premisEvent = addCreationEvent(dBpowerampLogs[0])
                self.premisCreationEvents.append(premisEvent)

            # Create Volume directory
            logging.info("creating carrier directory")
            dirVolume = os.path.join(
                SIPPath, self.carrierType, self.volumeNumber)
            try:
                os.makedirs(dirVolume)
            except (OSError, IOError):
                logging.fatal("jobID " + self.jobID +
                              ": cannot create '" + dirVolume + "'")
                config.errors += 1
                errorExit(config.errors, config.warnings)

            # Copy files to SIP Volume directory
            logging.info("copying files to carrier directory")

            # Get file names from checksum file, as this is the easiest way to make
            # post-copy checksum verification work. Filter out log files first!

            filesToCopy = [
                i for i in checksumsFromFile if not i[1].endswith(('.log', '.xml'))]

            for entry in filesToCopy:

                checksum = entry[0]
                fileName = entry[1]
                fileSize = entry[2]
                # Generate unique file ID (used in structMap)
                fileID = "file_" + str(sipFileCounter)
                # Construct path relative to carrier directory
                fIn = os.path.join(self.imagePathFull, fileName)

                # Construct path relative to volume directory
                fSIP = os.path.join(dirVolume, fileName)
                try:
                    # Copy to volume dir
                    shutil.copy2(fIn, fSIP)
                except OSError:
                    logging.fatal("jobID " + self.jobID +
                                  ": cannot copy '" +
                                  fileName + "' to '" + fSIP + "'")
                    config.errors += 1
                    errorExit(config.errors, config.warnings)

                # Calculate hash of copied file, and verify against known value
                checksumCalculated = checksums.generate_file_sha512(fSIP)
                if checksumCalculated != checksum:
                    logging.error("jobID " + self.jobID + ": checksum mismatch for file '" +
                                  fSIP + "'")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)

                # Create METS file and FLocat elements

                fileEltName = etree.QName(config.mets_ns, "file")
                fileElt = etree.Element(
                    fileEltName, nsmap=config.NSMAP)

                fileElt.attrib["ID"] = fileID
                fileElt.attrib["SIZE"] = fileSize

                fLocat = etree.SubElement(
                    fileElt, "{%s}FLocat" % (config.mets_ns))
                fLocat.attrib["LOCTYPE"] = "URL"
                # File locations relative to SIP root (= location of METS file)
                fLocat.attrib[etree.QName(config.xlink_ns, "href")] = "file:///" + \
                    self.carrierType + "/" + self.volumeNumber + "/" + fileName

                # Add MIME type and checksum to file element
                # Note: neither of these Mimetypes are formally registered at
                # IANA but they seem to be widely used. Also, DIAS filetypes list
                # uses /audio/x-wav!
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
                divFileName = etree.QName(config.mets_ns, "div")
                divFile = etree.Element(divFileName, nsmap=config.NSMAP)
                divFile.attrib["TYPE"] = mimeTypeMap[mimeType]
                divFile.attrib["ORDER"] = str(fileCounter)
                fptr = etree.SubElement(divFile, "{%s}fptr" % (config.mets_ns))
                fptr.attrib["FILEID"] = fileID

                # Add divisor element to divFileElements
                self.divFileElements.append(divFile)

                # Create techMD element for PREMIS object information
                techMDPremisName = etree.QName(config.mets_ns, "techMD")
                techMDPremis = etree.Element(techMDPremisName, nsmap=config.NSMAP)
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
                self.techMDFileElements.append(techMDPremis)

                # String of techMD identifiers that are used as ADMID attribute of fileElt
                techMDIDs = techMDPremisID

                # Add techMDIDs to fileElt
                fileElt.attrib["ADMID"] = techMDIDs

                # Add fileElt to fileElements
                self.fileElements.append(fileElt)

                fileCounter += 1
                sipFileCounter += 1
                counterTechMD += 1

        return sipFileCounter, counterTechMD
