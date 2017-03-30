#! /usr/bin/env python
from lxml import etree

if __package__ == 'omSipCreator':
    from . import config
else:
    import config
    
# Module for writing PREMIS metadata

def createEvent():
    # Create PREMIS event
    
    ## TEST
    eventName = etree.QName(config.premis_ns, "event")
    event = etree.Element(eventName, nsmap = config.NSMAP)
    ## TEST
         
    return(event)
