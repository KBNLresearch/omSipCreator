# Documentation of modules and processing flow


## omSipCreator

This module contains the main function, which does the following things:

- Set up a logger instance
- Define all namespaces and schemas for METS output
- Initialise package-wide shared flags and variables
- Get user input from the command-line
- Locate MediaInfo binaries
- Create a Batch instance (using *batch.Batch*)
- Process the batch using *batch.Batch.process*; prune the batch using *batch.Batch.prune* (only if the prune command was used)

## batch

This module contains the *Batch* class, which includes the functions *process* and *prune*.

### process function

Processes a batch, which involves the following steps:

- Parse the batch manifest and store the contents to two lists (one for the column headers, and one for the actual data)
- Do some basic checks on the data in the batch manifest (do all required columns exist; does every entry have the expected number of columns)
- Sort and group all entries in batch masnifest by PPN
- Then for each unique PPN value:
    * Create a PPN instance (using *ppn.PPN*)
    * Call the PPN processing function (using *ppn.proces*)
- Check if all directories in the batch that were encountered in the above step are represented in the batch manifest
- Collect any errors and warning that were encountered in the above steps

### prune function

- Create an error batch directory
- Copy directories for all PPNs for which errors were reported to the error batch (including post-copy checksum verification)
- For all PNN


### Input

### Output

## ppn

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

## carrier


## Naming

addCreationEvent, addAgent, addObjectInstance in premis.py: perhaps change *add* to *create* (since these functions do not *add* anything)
