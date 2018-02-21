# Documentation of main processing function 

## ppn.processPPN

### Input

### Output

## carrier.processCarrier

### Input

* carrier: Carrier class instance (created in processPPN) for this carrier
* SIPPath: SIP directory (config.dirOut/PPN)
* sipFileCounterStart: start value for within-SIP file counter
* counterTechMDStart: start value for within-SIP counterTechMD counter

### Output

Dictionary *carrierOut* with following elements:

* divFileElements: list with, *div* elements for all file-level structMap components (level 3 in SIP specification)
* fileElements: list, with *file* elements for all files that are part of carrier.
* techMDFileElements: list with file-level techMD elements
* premisCreationEvents: list with PREMIS imaging/ripping events (Isobuster/dBpoweramp logs)
* cdInfoElt: element, serialized cd-info output
* sipFileCounter: updated within-SIP file counter
* counterTechMD: updated within-SIP counterTechMD counter

## Naming

addCreationEvent, addAgent, addObjectInstance in premis.py: perhaps change *add* to *create* (since these functions do not *add* anything)
