#! /usr/bin/env python
from lxml import etree
import uuid

if __package__ == 'omSipCreator':
    from . import config
else:
    import config
    
# Module for writing PREMIS metadata

def createEvent():
    # Create PREMIS event
    
    eventName = etree.QName(config.premis_ns, "event")
    event = etree.Element(eventName, nsmap = config.NSMAP)
    eventIdentifier = etree.SubElement(event, "{%s}eventIdentifier" %(config.premis_ns))
    eventIdentifierType = etree.SubElement(eventIdentifier, "{%s}eventIdentifierType" %(config.premis_ns))
    eventIdentifierType.text = "UUID"
    eventIdentifierValue = etree.SubElement(eventIdentifier, "{%s}eventIdentifierValue" %(config.premis_ns))
    # Generate event identifier (UUID, based on host ID and current time)
    eventIdentifierValue.text = str(uuid.uuid1())
    
    return(event)
