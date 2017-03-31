#! /usr/bin/env python
from lxml import etree
import uuid

if __package__ == 'omSipCreator':
    from . import config
else:
    import config
    
# Module for writing PREMIS metadata

def createEvent(log):
    # Create PREMIS event
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
    
    # Event date/time: taken from timestamp of log file
    eventDateTime = etree.SubElement(event, "{%s}eventDateTime" %(config.premis_ns))
    
    return(event)
