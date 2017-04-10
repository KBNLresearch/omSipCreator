#! /usr/bin/env python
import os
import io
from datetime import datetime
from lxml import etree
import uuid

if __package__ == 'omSipCreator':
    from . import config
else:
    import config
    
# Module for writing PREMIS metadata

def addCreationEvent(log):

    # Read contents of log to a text string
    with io.open(log, "r", encoding="utf-8") as fLog:
        logContents = fLog.read()
    fLog.close()

    # Create PREMIS creation event
    eventName = etree.QName(config.premis_ns, "event")
    event = etree.Element(eventName, nsmap = config.NSMAP)
    
    # Event identifier: UUID, based on host ID and current time
    eventIdentifier = etree.SubElement(event, "{%s}eventIdentifier" %(config.premis_ns))
    eventIdentifierType = etree.SubElement(eventIdentifier, "{%s}eventIdentifierType" %(config.premis_ns))
    eventIdentifierType.text = "UUID"
    eventIdentifierValue = etree.SubElement(eventIdentifier, "{%s}eventIdentifierValue" %(config.premis_ns))
    eventIdentifierValue.text = str(uuid.uuid1())
    
    # Event type
    eventType = etree.SubElement(event, "{%s}eventType" %(config.premis_ns))
    eventType.text = "creation"
    
    # Event date/time: taken from timestamp of log file (last-modified)
    eventDateTimeValue = os.path.getctime(log)
    # Convert to formatted date/time string
    eventDateTimeFormatted = datetime.fromtimestamp(eventDateTimeValue).strftime('%Y-%m-%d %H:%M:%S')
    eventDateTime = etree.SubElement(event, "{%s}eventDateTime" %(config.premis_ns))
    eventDateTime.text = eventDateTimeFormatted
                
    # eventDetailInformation container with eventDetail element
    eventDetailInformation = etree.SubElement(event, "{%s}eventDetailInformation" %(config.premis_ns))
    eventDetail = etree.SubElement(eventDetailInformation, "{%s}eventDetail" %(config.premis_ns))
    
    # eventOutcomeInformation container
    eventOutcomeInformation = etree.SubElement(event, "{%s}eventOutcomeInformation" %(config.premis_ns))
    eventOutcomeDetail = etree.SubElement(eventOutcomeInformation, "{%s}eventOutcomeDetail" %(config.premis_ns))
    eventOutcomeDetailNote = etree.SubElement(eventOutcomeDetail, "{%s}eventOutcomeDetailNote" %(config.premis_ns))

    # linkingAgentIdentifier element
    linkingAgentIdentifier = etree.SubElement(event, "{%s}linkingAgentIdentifier" %(config.premis_ns))
    linkingAgentIdentifierType = etree.SubElement(linkingAgentIdentifier, "{%s}linkingAgentIdentifierType" %(config.premis_ns))
    linkingAgentIdentifierType.text = "URI"
    
    # Values of linkingAgentIdentifierValue and agentName are set further below
    linkingAgentIdentifierValue = etree.SubElement(linkingAgentIdentifier, "{%s}linkingAgentIdentifierValue" %(config.premis_ns))
    
    # Name of log
    logName = os.path.basename(log)
        
    eventOutcomeDetailNote.text = logContents
    
    isoBusterComment ="Isobuster error values:\n0       No Error (success)\n1       No Tracks / Sessions found\n2       Track Index provided but this track is not available\n3       Session Index provided but this Session is not available\n4       No File-system track found\n5       No (or not a matching) File-system found\n6       Folder name is already in use as filename\n7       Not a matching file or folder found\n10xx  Extraction aborted by user"
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
    return(event)
    
def addAgent(softwareName):

    # Create PREMIS agent instance
    agentName = etree.QName(config.premis_ns, "agent")
    agent = etree.Element(agentName, nsmap = config.NSMAP)
    agent = etree.SubElement(event, "{%s}agent" %(config.premis_ns))
    agentIdentifier = etree.SubElement(agent, "{%s}agentIdentifier" %(config.premis_ns))
    agentIdentifierType = etree.SubElement(agentIdentifier, "{%s}agentIdentifierType" %(config.premis_ns))
    agentIdentifierType.text = "URI"
    
    # Values of agentIdentifierValue and agentName are set further below
    agentIdentifierValue = etree.SubElement(agentIdentifier, "{%s}agentIdentifierValue" %(config.premis_ns))
    agentName = etree.SubElement(agent, "{%s}agentName" %(config.premis_ns))
    agentType = etree.SubElement(agent, "{%s}agentType" %(config.premis_ns))
    agentType.text = "software"
   
    if softwareName == "isobuster":
        # URI to isoBuster Wikidata page
        agentIdentifierValue.text = "https://www.wikidata.org/wiki/Q304733"
        agentName.text = "isoBuster"
    elif softwareName == "dbpoweramp":
        # URI to dBpoweramp Wikidata page
        agentIdentifierValue.text = "https://www.wikidata.org/wiki/Q1152133"
        agentName.text = "dBpoweramp"
        
    return(agent)


def addObjectInstance():

    # Create PREMIS object instance
    objectName = etree.QName(config.premis_ns, "object")
    object = etree.Element(objectName, nsmap = config.NSMAP)
    object.attrib["{%s}type" %config.xsi_ns] = "premis:file"
      
    # Object identifier
    objectIdentifier = etree.SubElement(object, "{%s}objectIdentifier" %(config.premis_ns))
    objectIdentifierType = etree.SubElement(objectIdentifier, "{%s}objectIdentifierType" %(config.premis_ns))
    objectIdentifierType.text = "UUID"
    objectIdentifierValue = etree.SubElement(objectIdentifier, "{%s}objectIdentifierValue" %(config.premis_ns))
    objectIdentifierValue.text = str(uuid.uuid1())
               
    return(object)
