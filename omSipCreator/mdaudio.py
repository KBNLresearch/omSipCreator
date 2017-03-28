#! /usr/bin/env python
from lxml import etree
import io

if __package__ == 'omSipCreator':
    from . import config
    from . import shared
else:
    import config
    import shared
    
# Wrapper module for mediainfo

def getTechMetadata(fileRef):
    args = [config.mediaInfoExe]
    args = [mediaInfoExe]
    args.append( "--Output=EBUCore")
    args.append(fileRef)
    
    # Command line as string (used for logging purposes only)
    cmdStr = " ".join(args)
     
    status, out, err = shared.launchSubProcess(args)
    
    # Parse string to element
    outElt = etree.fromstring(out.encode('utf-8'))
    
    # Main results to dictionary
    dictOut = {}
    dictOut["cmdStr"] = cmdStr
    dictOut["status"] = status
    dictOut["outElt"] = outElt
    dictOut["stderr"] = err
    
    return(dictOut)
