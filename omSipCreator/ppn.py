#! /usr/bin/env python
"""
Processing functions for one PPN
"""

import os
import sys
import logging
from operator import itemgetter
from itertools import groupby
from lxml import etree
from . import config
from .shared import errorExit
from .carrier import processCarrier
from .mods import createMODS


# Classes for Carrier and PPN

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
    def __init__(self, PPN):
        """initialise PPNGroup class instance"""
        self.carriers = []
        self.PPN = PPN
        self.carrierTypes = []

    def append(self, carrier):
        """Append a carrier"""
        self.carriers.append(carrier)
        self.carrierTypes.append(carrier.carrierType)


def processPPN(PPN, carriers):

    """Process a PPN"""
    # PPN is PPN identifier (by which we grouped data)
    # carriers is another iterator that contains individual carrier records

    # Create class instance for this PPN
    thisPPNGroup = PPNGroup(PPN)

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
        dirSIP = os.path.join(config.dirOut, PPN)
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
        volumeNumbersTypeGroup = []
        for carrier in carrierTypeGroup:

            jobID = carrier[config.colsBatchManifest["jobID"]]
            volumeNumber = carrier[config.colsBatchManifest["volumeNo"]]
            carrierType = carrier[config.colsBatchManifest["carrierType"]]
            title = carrier[config.colsBatchManifest["title"]]
            volumeID = carrier[config.colsBatchManifest["volumeID"]]
            success = carrier[config.colsBatchManifest["success"]]
            containsAudio = carrier[config.colsBatchManifest["containsAudio"]]
            containsData = carrier[config.colsBatchManifest["containsData"]]
            cdExtra = carrier[config.colsBatchManifest["cdExtra"]]

            # Update jobIDs list
            jobIDs.append(jobID)

            # Check for some obvious errors

            # Check if imagePath is existing directory

            # Full path, relative to batchIn TODO: check behaviour on Window$
            imagePathFull = os.path.normpath(os.path.join(config.batchIn, jobID))
            imagePathAbs = os.path.abspath(imagePathFull)

            # Append absolute path to list (used later for completeness check)
            config.dirsInMetaCarriers.append(imagePathAbs)

            if not os.path.isdir(imagePathFull):
                logging.error("jobID " + jobID + ": '" + imagePathFull +
                              "' is not a directory")
                config.errors += 1
                config.failedPPNs.append(PPN)

            # Create Carrier class instance for this carrier
            thisCarrier = Carrier(jobID, PPN, imagePathFull,
                                  volumeNumber, carrierType)
            fileElements, divDisc, premisEventsCarrier, techMDFileElements, cdInfoElt, fileCounter, counterTechMD = processCarrier(
                thisCarrier, dirSIP, fileCounterStart, counterTechMD)
            # NOTE
            # techMDFileElements: list of techMD elements, each of which represent one file.
            # Wraps EbuCore audio metdata + possibly other tech metadata
            # NOTE

            # Construct unique identifiers for digiProvMD and techMD (see below)
            # and add to divDisc as ADMID
            digiProvID = "digiprovMD_" + str(counterDigiprovMD)
            techID = "techMD_" + str(counterTechMD)
            divDisc.attrib["ADMID"] = " ".join([digiProvID, techID])

            # Append file elements to fileGrp
            for fileElement in fileElements:
                fileGrp.append(fileElement)

            # Append file-level techMD elements to amdSec
            for techMD in techMDFileElements:
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
            xmlDatatechMDRep.append(cdInfoElt)

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

            techMDRepElements.append(techMDRep)
            digiProvElements.append(digiprovMD)

            # Add to PPNGroup class instance
            thisPPNGroup.append(thisCarrier)

            # Update fileCounterStart
            fileCounterStart = fileCounter

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
            if carrierType not in config.carrierTypeAllowedValues:
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

    # Append sourceMD and digiProvMD elements to amdSec
    for element in techMDRepElements:
        amdSec.append(element)
    for element in digiProvElements:
        amdSec.append(element)

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
