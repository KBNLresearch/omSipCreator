#! /usr/bin/env python

"""
Wrapper module for mediainfo
"""

from lxml import etree
from . import config
from . import shared


def getAudioMetadata(fileRef):
    """Extract metadata for audio file"""
    args = [config.mediaInfoExe]
    args.append("--Output=EBUCore")
    args.append(fileRef)

    # Command line as string (used for logging purposes only)
    cmdStr = " ".join(args)

    status, out, err = shared.launchSubProcess(args)

    # Configure XML parser to get rid of blank lines in MediaInfo output
    parser = etree.XMLParser(remove_blank_text=True)

    # Parse string to element
    outElt = etree.XML(out.encode('utf-8'), parser=parser)

    # Main results to dictionary
    dictOut = {}
    dictOut["cmdStr"] = cmdStr
    dictOut["status"] = status
    dictOut["outElt"] = outElt
    dictOut["stderr"] = err

    return dictOut
