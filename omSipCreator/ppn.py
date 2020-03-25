#! /usr/bin/env python
"""
Class and processing functions for one PPN
"""

import os
import sys
import logging
from operator import itemgetter
from itertools import groupby
from lxml import etree
from . import config
from .carrier import Carrier
from .shared import errorExit
from .mods import createMODS


# PPN class

class PPN:
    """PPN class"""
    def __init__(self, PPNValue):
        """initialise PPN class instance"""
        self.carriers = []
        self.PPN = PPNValue
        self.carrierTypes = []

    def append(self, carrier):
        """Append a carrier"""
        self.carriers.append(carrier)
        self.carrierTypes.append(carrier.carrierType)

    def process(self, carriers, batchDir, colsBatchManifest):

        """Process a PPN"""
        # PPN is PPN identifier (by which we grouped data)
        # carriers is another iterator that contains individual carrier records

        # Create METS element for this SIP
        metsName = etree.QName(config.mets_ns, "mets")
        mets = etree.Element(metsName, nsmap=config.NSMAP)
        # Add schema reference
        mets.attrib[etree.QName(config.xsi_ns, "schemaLocation")] = "".join(
            [config.metsSchema, " ", config.modsSchema, " ", config.premisSchema])
        # Add TYPE attribute
        mets.attrib["TYPE"] = "SIP"
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
        sipFileCounterStart = 1
        counterTechMDStart = 1
        carrierCounter = 1
        counterDigiprovMD = 1

        # Dummy value for dirSIP (needed if createSIPs = False)
        dirSIP = "rubbish"

        if config.createSIPs:
            logging.info("creating SIP directory")
            # Create SIP directory
            dirSIP = os.path.join(config.dirOut, self.PPN)
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

        # Set up list that will is used to collect all representation-level techMD and
        # digiProv elements for all carriers within PPN
        techMDRepElements = []
        digiProvElements = []

        # Convert to list (needed because othwerwise we can't sort)
        carriers = list(carriers)
        # Sort rows by carrier type
        carriers.sort(key=itemgetter(3))
        carriersByType = groupby(carriers, itemgetter(3))

        for carrierTypeCarriers, carrierTypeGroup in carriersByType:
            for carrier in carrierTypeGroup:

                jobID = carrier[colsBatchManifest["jobID"]]
                volumeNumber = carrier[colsBatchManifest["volumeNo"]]
                title = carrier[colsBatchManifest["title"]]
                volumeID = carrier[colsBatchManifest["volumeID"]]
                success = carrier[colsBatchManifest["success"]]
                containsAudio = carrier[colsBatchManifest["containsAudio"]]
                containsData = carrier[colsBatchManifest["containsData"]]
                cdExtra = carrier[colsBatchManifest["cdExtra"]]

                if config.iromlabMajorVersion == 1:
                    mixedMode = carrier[colsBatchManifest["mixedMode"]]
                    cdInteractive = carrier[colsBatchManifest["cdInteractive"]]
                else:
                    mixedMode = "False"
                    cdInteractive = "False"

                # Update jobIDs list
                jobIDs.append(jobID)

                # Check for some obvious errors

                # Check if imagePath is existing directory

                # Full path, relative to batchIn TODO: check behaviour on Window$
                imagePathFull = os.path.normpath(os.path.join(batchDir, jobID))
                imagePathAbs = os.path.abspath(imagePathFull)

                # Append absolute path to list (used later for completeness check)
                config.dirsInMetaCarriers.append(imagePathAbs)

                if not os.path.isdir(imagePathFull):
                    logging.error("jobID " + jobID + ": '" + imagePathFull +
                                  "' is not a directory")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)
                
                # Create Carrier class instance for this carrier
                thisCarrier = Carrier(jobID, self.PPN, imagePathFull,
                                      volumeNumber)

                # Process carrier
                sipFileCounter, counterTechMD = thisCarrier.process(dirSIP,
                                                                    sipFileCounterStart,
                                                                    counterTechMDStart)

                # Set carrierType value, based on Isobuster carrier type and info read
                # from batch manifest. TODO: could be more fine-grained for CD-Extra,
                # cd-i, etc.

                if thisCarrier.isobusterCarrierType == "DVD":
                    # TODO:
                    # 1. Check if value reported by Isobuster is really "DVD" 
                    # 2. Update resourceTypeMap in mods.py, which also contains dvd-video.
                    #    Probably better to merge both in one generic dvd class
                    carrierType = "dvd-rom"
                elif cdInteractive == "True":
                    carrierType = "cd-interactive"
                elif cdExtra == "True":
                    # TODO: vaguely recall cd-info flagging mixed mode CDs as cd-extra as well,
                    # or vice versa. If so needs additional exclusion here.
                    carrierType = "cd-extra"
                elif mixedMode == "True":
                    # TODO: vaguely recall cd-info flagging mixed mode CDs as cd-extra as well,
                    # or vice versa. If so needs additional exclusion here.
                    carrierType = "cd-mixedmode"
                elif containsData == "True":
                    carrierType = "cd-rom"
                elif containsAudio == "True":
                    carrierType = "cd-audio"
                else:
                    # Bogus value, needed below
                    carrierType = "unknown"
 
                # Append file elements to fileGrp
                for fileElement in thisCarrier.fileElements:
                    fileGrp.append(fileElement)

                # Create carrier-level METS div entry
                divDiscName = etree.QName(config.mets_ns, "div")
                divDisc = etree.Element(divDiscName, nsmap=config.NSMAP)
                divDisc.attrib["TYPE"] = carrierType
                divDisc.attrib["ORDER"] = thisCarrier.volumeNumber

                # Construct unique identifiers for digiProvMD and techMD (see below)
                # and add to divDisc as ADMID
                digiProvID = "digiprovMD_" + str(counterDigiprovMD)
                techID = "techMD_" + str(counterTechMD)
                divDisc.attrib["ADMID"] = " ".join([digiProvID, techID])

                # Append file-level div elements to carrier-level div element
                for divFile in thisCarrier.divFileElements:
                    divDisc.append(divFile)

                # Update structmap in METS
                structDivTop.append(divDisc)

                # Append file-level techMD elements to amdSec
                for techMD in thisCarrier.techMDFileElements:
                    amdSec.append(techMD)

                counterTechMD += 1

                # Create representation-level techMD, digiprovMD, mdWrap and xmlData
                # child elements
                techMDRepName = etree.QName(config.mets_ns, "techMD")
                techMDRep = etree.Element(techMDRepName, nsmap=config.NSMAP)
                techMDRep.attrib["ID"] = techID
                mdWrapTechMDRep = etree.SubElement(
                    techMDRep, "{%s}mdWrap" % (config.mets_ns))
                mdWrapTechMDRep.attrib["MIMETYPE"] = "text/xml"
                mdWrapTechMDRep.attrib["MDTYPE"] = "OTHER"
                mdWrapTechMDRep.attrib["OTHERMDTYPE"] = "cd-info output"
                xmlDatatechMDRep = etree.SubElement(
                    mdWrapTechMDRep, "{%s}xmlData" % (config.mets_ns))
                xmlDatatechMDRep.append(thisCarrier.cdInfoElt)

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
                for premisEvent in thisCarrier.premisCreationEvents:
                    xmlDatadigiprov.append(premisEvent)

                techMDRepElements.append(techMDRep)
                digiProvElements.append(digiprovMD)

                # Add to PPNGroup class instance
                self.append(thisCarrier)

                # Update counters
                sipFileCounterStart = sipFileCounter
                counterTechMDStart = counterTechMD
                carrierCounter += 1
                counterDigiprovMD += 1

                # convert volumeNumber to integer (so we can do more checking below)
                try:
                    volumeNumbers.append(int(volumeNumber))
                except ValueError:
                    # Raises error if volumeNumber string doesn't represent integer
                    logging.error("jobID " + jobID + ": '" + volumeNumber +
                                  "' is illegal value for 'volumeNumber' (must be integer)")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)

                # Check carrierType value against controlled vocabulary
                if carrierType not in config.carrierTypeAllowedValues:
                    logging.error("jobID " + jobID + ": '" + carrierType +
                                  "' is illegal value for 'carrierType'")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)
                carrierTypes.append(carrierType)

                # Check success value (status)
                if success != "True":
                    logging.error("jobID " + jobID +
                                  ": value of 'success' not 'True'")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)

                # Check if carrierType value is consistent with containsAudio and containsData
                if carrierType in ["cd-rom", "dvd-rom", "dvd-video"] and containsData != "True":
                    logging.error("jobID " + jobID + ": carrierType cannot be '" +
                                  carrierType + "'if 'containsData' is 'False'")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)
                elif carrierType == "cd-audio" and containsAudio != "True":
                    logging.error("jobID " + jobID + ": carrierType cannot be '" +
                                  carrierType + "'if 'containsAudio' is 'False'")
                    config.errors += 1
                    config.failedPPNs.append(self.PPN)


        # Get metadata of this PPN from catalogue and convert to MODS format
        mdMODS = createMODS(self)

        # Append metadata to METS
        xmlDataDmd.append(mdMODS)

        # Append techMD and digiProvMD elements to amdSec
        for element in techMDRepElements:
            amdSec.append(element)
        for element in digiProvElements:
            amdSec.append(element)

        if config.createSIPs:
            logging.info("writing METS file")
            metsAsString = etree.tostring(
                mets, pretty_print=True, encoding="unicode")
            metsFname = os.path.join(dirSIP, "mets.xml")

            with open(metsFname, "w", encoding="utf-8") as text_file:
                text_file.write(metsAsString)

        # IP-level consistency checks

        # jobID values must all be unique (no duplicates!)
        uniquejobIDs = set(jobIDs)
        if len(uniquejobIDs) != len(jobIDs):
            logging.error("PPN " + self.PPN + ": duplicate values found for 'jobID'")
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Consistency checks on volumeNumber values

        # Volume numbers must be unique
        uniqueVolumeNumbers = set(volumeNumbers)
        if len(uniqueVolumeNumbers) != len(volumeNumbers):
            logging.error("PPN " + self.PPN + " (" + carrierType +
                          "): duplicate values found for 'volumeNumber'")
            config.errors += 1
            config.failedPPNs.append(self.PPN)

        # Report warning if lower value of volumeNumber not equal to '1'
        volumeNumbers.sort()
        if volumeNumbers[0] != 1:
            logging.warning("PPN " + self.PPN + " (" + carrierType +
                            "): expected '1' as lower value for 'volumeNumber', found '" +
                            str(volumeNumbers[0]) + "'")
            config.warnings += 1

        # Report warning if volumeNumber does not contain consecutive numbers
        # (indicates either missing volumes or data entry error)

        if sorted(volumeNumbers) != list(range(min(volumeNumbers),
                                                        max(volumeNumbers) + 1)):
            logging.warning("PPN " + self.PPN + " (" + carrierType +
                            "): values for 'volumeNumber' are not consecutive")
            config.warnings += 1
