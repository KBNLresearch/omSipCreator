#! /usr/bin/env python
"""
Class and processing functions for scans directory of one PPN
"""

import os
import ntpath
import shutil
import glob
import logging
from operator import itemgetter
from lxml import etree
from . import config
from . import checksums
from .shared import errorExit
from .premis import addCreationEvent
from .premis import addObjectInstance


class Scans:
    """Scans class"""
    def __init__(self, PPN, scansDirPPN):
        """Initialise Carrier class instance"""
        self.PPN = PPN
        self.scansDirPPN = scansDirPPN
        self.scansDirNameSIP = "scans"
        self.divFileElements = []
        self.fileElements = []
        self.techMDFileElements = []
        self.premisCreationEvents = []
        #cdInfoName = etree.QName(config.cdInfo_ns, "cd-info")
        #self.cdInfoElt = etree.Element(cdInfoName, nsmap=config.NSMAP)

    def process(self, SIPPath, sipFileCounterStart, counterTechMDStart):
        """Process scans directory for one PPN"""

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
        allFiles = glob.glob(self.scansDirPPN + "/*")

        # Find info files (by extension)
        infoFiles = [i for i in allFiles if i.endswith('.xml')]

        # Number of info files must be exactly 1
        noInfoFiles = len(infoFiles)

        if noInfoFiles != 1:
            logging.error("PPN " + self.PPN + ": found " + str(noInfoFiles) +
                          " info files in directory '" +
                          self.scansDirPPN + "', expected 1")
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Any other files (scanned images)
        otherFiles = [i for i in allFiles if not i.endswith(('.xml'))]
        noOtherFiles = len(otherFiles)

        if noOtherFiles == 0:
            logging.error("PPN " + self.PPN + ": found no files in directory '" +
                          self.scansDirPPN)
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Nested list to store file names and checksum values
        checksumsFromFile = []

        # Read contents of info file
        try:
            infoElt = etree.parse(infoFiles[0]).getroot()
        except:
            logging.error("PPN " + self.PPN +
                            ": error parsing '" + infoFiles[0] + "'")
            config.errors += 1
            config.failedPPNs.append(self.PPN)
        try:
            scannerName = infoElt.xpath('//info/scanner/info/name')[0].text
            scannerDriver = infoElt.xpath('//info/scanner/info/driver')[0].text
            scannerDpi = infoElt.xpath('//info/scanner/info/dpi')[0].text
            scannerColordepth = infoElt.xpath('//info/scanner/info/colordepth')[0].text
            scannerOutputformat = infoElt.xpath('//info/scanner/info/outputformat')[0].text
            scanElts = infoElt.xpath('//scans/scan')

            for scanElt in scanElts:
                fileRef = scanElt.find('file').text
                checksum = scanElt.find('checksum').text
                checksumType = scanElt.find('checksum').get('type')

                # fileRef is absolute paths, so strip away everything but file name
                fileName = ntpath.basename(fileRef)
                checksumsFromFile.append([checksum, fileName])
        except:
            raise
            logging.error("PPN " + self.PPN +
                            ": error processing '" + infoFiles[0] + "'")
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Sort ascending by file name - this ensures correct order when making structMap
        checksumsFromFile.sort(key=itemgetter(1))

        # List to store names of all files that are referenced in the info file
        allFilesinChecksumFile = []
        for entry in checksumsFromFile:
            checksum = entry[0]
            # Raises IndexError if entry only 1 col (malformed checksum file)!
            fileName = entry[1]
            # Normalise file path relative to imagePath
            fileNameWithPath = os.path.normpath(
                self.scansDirPPN + "/" + fileName)

            # Calculate SHA-512 hash of actual file
            if os.path.isfile(fileNameWithPath) and config.skipChecksumFlag == False:
                checksumCalculated = checksums.generate_file_sha512(fileNameWithPath)
            elif os.path.isfile(fileNameWithPath) and config.skipChecksumFlag == True:
                checksumCalculated = "bogus"
            else:
                logging.fatal("PPN " + self.PPN + ": file '" +
                              fileNameWithPath + "' is referenced in '" + infoFiles[0] +
                              "', but does not exist")
                config.errors += 1
                config.failedPPNs.append(self.PPN)
                errorExit(config.errors, config.warnings)

            if checksumCalculated != checksum and config.skipChecksumFlag == False:
                logging.error("PPN " + self.PPN + ": checksum mismatch for file '" +
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
                logging.error("PPN " + self.PPN + ": file '" + f +
                              "' not referenced in '" +
                              infoFiles[0] + "'")
                config.errors += 1
                config.failedPPNs.append(self.PPN)

        if config.createSIPs:

            # Create scans directory
            # TODO: naming of this dir?
            logging.info("creating scans directory")
            dirScans = os.path.join(
                SIPPath, self.scansDirNameSIP)
            try:
                os.makedirs(dirScans)
            except (OSError, IOError):
                logging.fatal("PPN " + self.PPN +
                              ": cannot create '" + dirScans + "'")
                config.errors += 1
                config.failedPPNs.append(self.PPN)
                errorExit(config.errors, config.warnings)

            # Copy files to scans directory
            logging.info("copying files to scans directory")

            # Get file names from checksums list, as this is the easiest way to make
            # post-copy checksum verification work. Filter out log files first!

            filesToCopy = [
                i for i in checksumsFromFile if i[1].endswith(('.tif', '.tiff', '.TIF', '.TIFF'))]

            for entry in filesToCopy:

                checksum = entry[0]
                fileName = entry[1]
                fileSize = entry[2]
                # Generate unique file ID (used in structMap)
                fileID = "file_" + str(sipFileCounter)
                # Construct path relative to scans directory
                fIn = os.path.join(self.scansDirPPN, fileName)

                # Construct path relative to scans directory
                fSIP = os.path.join(dirScans, fileName)
                try:
                    # Copy to volume dir
                    shutil.copy2(fIn, fSIP)
                except OSError:
                    logging.fatal("PPN " + self.PPN +
                                  ": cannot copy '" +
                                  fileName + "' to '" + fSIP + "'")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)
                    errorExit(config.errors, config.warnings)

                # Calculate hash of copied file, and verify against known value
                checksumCalculated = checksums.generate_file_sha512(fSIP)
                if checksumCalculated != checksum:
                    logging.error("PPN " + self.PPN + ": checksum mismatch for file '" +
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
                    self.scansDirNameSIP + "/" + fileName

                # Add MIME type and checksum to file element
                # TODO: use proper magic-based identification
                if fileName.endswith(('.tif', '.tiff', '.TIF', '.TIFF')):
                    mimeType = "image/tiff"
                else:
                    mimeType = "application/octet-stream"
                fileElt.attrib["MIMETYPE"] = mimeType
                fileElt.attrib["CHECKSUM"] = checksum
                fileElt.attrib["CHECKSUMTYPE"] = "SHA-512"

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
                    fSIP, fileSize, mimeType, checksum)
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
