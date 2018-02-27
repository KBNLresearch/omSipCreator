#! /usr/bin/env python

"""
Module for writing PREMIS metadata
"""

import os
import io
import uuid
from datetime import datetime
import xml.etree.ElementTree as ET
import pytz
from lxml import etree
from isolyzer import isolyzer
from . import config
from .mdaudio import getAudioMetadata
from .shared import makeHumanReadable
from .shared import add_ns_prefix


def addCreationEvent(log):

    """Generate creation event using info from log file of creation application"""

    # Read contents of log to a text string
    with io.open(log, "r", encoding="utf-8") as fLog:
        logContents = fLog.read()
    fLog.close()

    # Create PREMIS creation event
    eventName = etree.QName(config.premis_ns, "event")
    event = etree.Element(eventName, nsmap=config.NSMAP)

    # Event identifier: UUID, based on host ID and current time
    eventIdentifier = etree.SubElement(
        event, "{%s}eventIdentifier" % (config.premis_ns))
    eventIdentifierType = etree.SubElement(
        eventIdentifier, "{%s}eventIdentifierType" % (config.premis_ns))
    eventIdentifierType.text = "UUID"
    eventIdentifierValue = etree.SubElement(
        eventIdentifier, "{%s}eventIdentifierValue" % (config.premis_ns))
    eventIdentifierValue.text = str(uuid.uuid1())

    # Event type
    eventType = etree.SubElement(event, "{%s}eventType" % (config.premis_ns))
    eventType.text = "creation"

    # Event date/time: taken from timestamp of log file (last-modified)
    eventDateTimeValue = datetime.fromtimestamp(os.path.getctime(log))
    # Add time zone info
    pst = pytz.timezone('Europe/Amsterdam')
    eventDateTimeValue = pst.localize(eventDateTimeValue)
    eventDateTimeFormatted = eventDateTimeValue.isoformat()

    eventDateTime = etree.SubElement(
        event, "{%s}eventDateTime" % (config.premis_ns))
    eventDateTime.text = eventDateTimeFormatted

    # eventDetailInformation container with eventDetail element
    eventDetailInformation = etree.SubElement(
        event, "{%s}eventDetailInformation" % (config.premis_ns))
    eventDetail = etree.SubElement(
        eventDetailInformation, "{%s}eventDetail" % (config.premis_ns))

    # eventOutcomeInformation container
    eventOutcomeInformation = etree.SubElement(
        event, "{%s}eventOutcomeInformation" % (config.premis_ns))
    eventOutcomeDetail = etree.SubElement(
        eventOutcomeInformation, "{%s}eventOutcomeDetail" % (config.premis_ns))
    eventOutcomeDetailNote = etree.SubElement(
        eventOutcomeDetail, "{%s}eventOutcomeDetailNote" % (config.premis_ns))

    # linkingAgentIdentifier element
    linkingAgentIdentifier = etree.SubElement(
        event, "{%s}linkingAgentIdentifier" % (config.premis_ns))
    linkingAgentIdentifierType = etree.SubElement(
        linkingAgentIdentifier, "{%s}linkingAgentIdentifierType" % (config.premis_ns))
    linkingAgentIdentifierType.text = "URI"

    # Values of linkingAgentIdentifierValue and agentName are set further below
    linkingAgentIdentifierValue = etree.SubElement(
        linkingAgentIdentifier, "{%s}linkingAgentIdentifierValue" % (config.premis_ns))

    # Name of log
    logName = os.path.basename(log)

    eventOutcomeDetailNote.text = logContents

    isoBusterComment = "Isobuster error values:\n \
        0       No Error (success)\n \
        1       No Tracks / Sessions found\n \
        2       Track Index provided but this track is not available\n \
        3       Session Index provided but this Session is not available\n \
        4       No File-system track found\n \
        5       No (or not a matching) File-system found\n \
        6       Folder name is already in use as filename\n \
        7       Not a matching file or folder found\n \
        10xx  Extraction aborted by user"

    comment = etree.Comment(isoBusterComment)

    if logName == "isobuster.log":
        eventDetail.text = "Image created with IsoBuster"
        eventOutcomeDetail.insert(1, comment)
        # URI to isoBuster Wikidata page
        linkingAgentIdentifierValue.text = "https://www.wikidata.org/wiki/Q304733"
    elif logName == "dbpoweramp.log":
        # URI to dBpoweramp Wikidata page
        eventDetail.text = "Audio ripped with dBpoweramp"
        # URI to dBpoweramp Wikidata page
        linkingAgentIdentifierValue.text = "https://www.wikidata.org/wiki/Q1152133"
    return event


def addAgent(softwareName):

    """Generate agent instance for creation software"""
    # TODO: do we need this function?

    # Create PREMIS event
    eventName = etree.QName(config.premis_ns, "event")
    event = etree.Element(eventName, nsmap=config.NSMAP)

    # Create PREMIS agent instance
    agentName = etree.QName(config.premis_ns, "agent")
    agent = etree.Element(agentName, nsmap=config.NSMAP)
    agent = etree.SubElement(event, "{%s}agent" % (config.premis_ns))
    agentIdentifier = etree.SubElement(
        agent, "{%s}agentIdentifier" % (config.premis_ns))
    agentIdentifierType = etree.SubElement(
        agentIdentifier, "{%s}agentIdentifierType" % (config.premis_ns))
    agentIdentifierType.text = "URI"

    # Values of agentIdentifierValue and agentName are set further below
    agentIdentifierValue = etree.SubElement(
        agentIdentifier, "{%s}agentIdentifierValue" % (config.premis_ns))
    agentName = etree.SubElement(agent, "{%s}agentName" % (config.premis_ns))
    agentType = etree.SubElement(agent, "{%s}agentType" % (config.premis_ns))
    agentType.text = "software"

    if softwareName == "isobuster":
        # URI to isoBuster Wikidata page
        agentIdentifierValue.text = "https://www.wikidata.org/wiki/Q304733"
        agentName.text = "isoBuster"
    elif softwareName == "dbpoweramp":
        # URI to dBpoweramp Wikidata page
        agentIdentifierValue.text = "https://www.wikidata.org/wiki/Q1152133"
        agentName.text = "dBpoweramp"

    return agent


def addObjectInstance(fileName, fileSize, mimeType, sha512Sum, sectorOffset, isobusterReportElt):

    """Generate object instance for file"""

    # Dictionary that links formatName values to mimeTypes
    formatNames = {
        # From LoC: https://www.loc.gov/preservation/digital/formats/fdd/fdd000348.shtml
        'application/x-iso9660-image': 'ISO_Image',
        'audio/wav': 'Wave',  # from DIAS filetypes list
        'audio/flac': 'FLAC'  # Not on DIAS filetypes list
    }
    # Dictionary that links DIAS fileTypeID values to mimeTypes
    fileTypeIDs = {
        'application/x-iso9660-image': 'n/a',  # Not on DIAS filetypes list
        'audio/wav': '60',
        'audio/flac': 'n/a'  # Not on DIAS filetypes list
    }
    # Create PREMIS object instance
    objectName = etree.QName(config.premis_ns, "object")
    pObject = etree.Element(objectName, nsmap=config.NSMAP)
    pObject.attrib["{%s}type" % config.xsi_ns] = "premis:file"

    # Object identifier
    objectIdentifier = etree.SubElement(
        pObject, "{%s}objectIdentifier" % (config.premis_ns))
    objectIdentifierType = etree.SubElement(
        objectIdentifier, "{%s}objectIdentifierType" % (config.premis_ns))
    objectIdentifierType.text = "UUID"
    objectIdentifierValue = etree.SubElement(
        objectIdentifier, "{%s}objectIdentifierValue" % (config.premis_ns))
    objectIdentifierValue.text = str(uuid.uuid1())

    # Object characteristics
    objectCharacteristics = etree.SubElement(
        pObject, "{%s}objectCharacteristics" % (config.premis_ns))
    compositionLevel = etree.SubElement(
        objectCharacteristics, "{%s}compositionLevel" % (config.premis_ns))
    compositionLevel.text = "0"

    # Fixity element for SHA-512 checksum
    fixity1 = etree.SubElement(
        objectCharacteristics, "{%s}fixity" % (config.premis_ns))
    messageDigestAlgorithm = etree.SubElement(
        fixity1, "{%s}messageDigestAlgorithm" % (config.premis_ns))
    messageDigestAlgorithm.text = "SHA-512"
    messageDigest = etree.SubElement(
        fixity1, "{%s}messageDigest" % (config.premis_ns))
    messageDigest.text = sha512Sum
    messageDigestOriginator = etree.SubElement(
        fixity1, "{%s}messageDigestOriginator" % (config.premis_ns))
    # Value more or less follows convention for DM 1.5
    messageDigestOriginator.text = "python.hashlib.sha512.hexdigest"

    # Size
    size = etree.SubElement(objectCharacteristics,
                            "{%s}size" % (config.premis_ns))
    size.text = fileSize

    # Format
    pFormat = etree.SubElement(objectCharacteristics,
                               "{%s}format" % (config.premis_ns))
    formatDesignation = etree.SubElement(
        pFormat, "{%s}formatDesignation" % (config.premis_ns))
    formatName = etree.SubElement(
        formatDesignation, "{%s}formatName" % (config.premis_ns))

    # Lookup formatName for mimeType
    formatName.text = formatNames.get(mimeType)

    # formatRegistry: DIAS fileTypeID values
    # TODO FLAC and ISO Image fmts have no fileTypeID values. These either have to be added to the
    # DIAS filetypes list or the formatRegistry element should be omitted altogether
    formatRegistry = etree.SubElement(
        pFormat, "{%s}formatRegistry" % (config.premis_ns))
    formatRegistryName = etree.SubElement(
        formatRegistry, "{%s}formatRegistryName" % (config.premis_ns))
    formatRegistryName.text = "DIAS"
    formatRegistryKey = etree.SubElement(
        formatRegistry, "{%s}formatRegistryKey" % (config.premis_ns))
    formatRegistryKey.text = fileTypeIDs.get(mimeType)

    # objectCharacteristicsExtension - EBUCore, isolyzer, Isobuster DFXML
    objectCharacteristicsExtension1 = etree.SubElement(
        objectCharacteristics, "{%s}objectCharacteristicsExtension" % (config.premis_ns))

    if fileName.endswith(('.wav', '.WAV', 'flac', 'FLAC')):
        audioMDOut = getAudioMetadata(fileName)
        audioMD = audioMDOut["outElt"]
        objectCharacteristicsExtension1.append(audioMD)
    elif fileName.endswith(('.iso', '.ISO')):
        # Add Isobuster's DFXML report
        isobusterReportElt = add_ns_prefix(isobusterReportElt, config.dfxml_ns)
        objectCharacteristicsExtension1.append(isobusterReportElt)

        # Add another objectCharacteristicsExtension element for Isolyzer output
        objectCharacteristicsExtension2 = etree.SubElement(
            objectCharacteristics, "{%s}objectCharacteristicsExtension" % (config.premis_ns))
        # Analyze ISO image with isolyzer
        isolyzerOut = isolyzer.processImage(fileName, sectorOffset)
        # Isolyzer output is Elementtree element, which must be converted
        # to lxml element
        makeHumanReadable(isolyzerOut)
        isolyzerOutAsXML = ET.tostring(isolyzerOut, 'UTF-8', 'xml')
        isolyzerOutLXML = etree.fromstring(isolyzerOutAsXML)
        isolyzerOutLXML = add_ns_prefix(isolyzerOutLXML, config.isolyzer_ns)
        isoMDOut = etree.Element("{%s}isolyzer" % (config.isolyzer_ns), nsmap=config.NSMAP)
        toolInfo = etree.SubElement(isoMDOut, "{%s}toolInfo" % (config.isolyzer_ns))
        toolName = etree.SubElement(toolInfo, "{%s}toolName" % (config.isolyzer_ns))
        toolVersion = etree.SubElement(toolInfo, "{%s}toolVersion" % (config.isolyzer_ns))
        toolName.text = "isolyzer"
        toolVersion.text = isolyzer.__version__
        isoMDOut.append(isolyzerOutLXML)
        objectCharacteristicsExtension2.append(isoMDOut)

    # originalName
    originalName = etree.SubElement(
        pObject, "{%s}originalName" % (config.premis_ns))
    originalName.text = os.path.basename(fileName)

    return pObject
