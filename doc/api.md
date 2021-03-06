# Documentation of modules and processing flow

The general flow of the software is as follows:

- Module *omSipCreator* contains the main function, which calls the *batch.Batch.process* function to process the batch
- The *batch.Batch.process* function calls *ppn.PPN.process* for each PPN in the batch
- The *ppn.PPN.process* function calls the *carrier.Carrier.process* function for each carrier that belongs to the PPN
- In addition to the above, if the *prune* command was used, the *omSipCreator* main function calls the *batch.Batch.prune* function to prune the batch

In addition to the above modules there are also some helper modules for e.g. generating metadata (MODS, PREMIS, EBUCore).

Below follows a description of the most important modules and their underlying functions.

## Module *omSipCreator*

This module contains the main function, which does the following things:

- Set up a logger instance
- Define all namespaces and schemas for METS output
- Initialise package-wide shared flags and variables
- Get user input from the command-line
- Locate MediaInfo binaries
- Create a Batch instance (using *batch.Batch*)
- Process the batch using *batch.Batch.process*; prune the batch using *batch.Batch.prune* (only if the *prune* command was used)

## Module *batch*

This module contains the *Batch* class, which represents a batch and its properties. It includes the functions *process* and *prune*.

### Function *process*

Processes a batch.

#### Processing steps

- Parse the batch manifest and store the contents to two lists (one for the column headers, and one for the actual data)
- Do some basic checks on the data in the batch manifest (do all required columns exist; does every entry have the expected number of columns)
- Sort and group all entries in batch manifest by PPN
- Then for each unique PPN value:
    * Create a PPN instance (using *ppn.PPN*)
    * Call the PPN processing function (using *ppn.PPN.proces*)
- Check if all directories in the batch that were encountered in the above step are represented in the batch manifest
- Collect any errors and warnings that were encountered in the above steps
- Report errors/warnings to *stdout*

### Function *prune*

Prunes a batch.

#### Processing steps

- Create an error batch directory
- Copy directories for all PPNs for which errors were reported to the error batch (including post-copy checksum verification); exit if checksum verification fails
- Update batch manifest in source batch + make copy of original batch manifest. Make batch manifest for error batch
- Collect any errors and warning that were encountered in the above steps
- Report additional errors/warnings that happened at pruning stage to *stdout*

## Module *ppn*

This module contains the *PPN* class, which represents a PPN (or more precisely, an intellectual entity that corresponds to a PPN, which in turn comprises all carriers that are to be included in one SIP) and its properties. It includes the function *process*.

### Function *process*

Processes one intellectual entity.

#### Input arguments

- carriers: batch manifest rows for all carriers that are part of a PPN
- batchDir: full path to batch directory
- colsBatchManifest: dictionary with, for each batch manifest header field, the corresponding column number

#### Processing steps

- Create a METS element and its top-level subelements
- Initialise counters that are used to assign file- and carrier-level identifiers in the METS for this SIP
- Create a SIP directory (only if the *write* command is used)
- Sort and group all carriers that belong to this PPN by carrier type
- For each carrier:
    * Create a Carrier instance (using *carrier.Carrier*)
    * Call the Carrier processing function (using *carrier.Carrier.process*)
    * Append all *file* elements for this carrier (generated by  *carrier.Carrier.process*) to the *fileGrp* element in the METS *fileSec* section
    * Append all file-level *div* elements (generated by  *carrier.Carrier.process*) to the the carrier-level *div* element in the METS *structMap* section
    * Append all file-level *techMD* elements (generated by  *carrier.Carrier.process*) to the METS *amdSec* section
    * Create a carrier-level *techMD* element and append the serialized cd-info output element (generated by  *carrier.Carrier.process*) to it
    * Create a carrier-level *digiprovMD* element and append the PREMIS creation events (generated by  *carrier.Carrier.process*) to it
    * Do some quality and consistency checks on the batch manifest entry for this carrier
- Query catalogue for bibliographical metadata, convert to MODS (using *mods.createMODS* function) and append result to METS *dmdSec* section
- Append carrier-level *techMD* and *digiProvMD* elements to the METS *amdSec* section
- Write the METS file to disk (only if the *write* command is used)
- Do some SIP-level consistency checks
- Collect any errors and warnings that were encountered in the above steps

## Module *carrier*

This module contains the *Carrier* class, which represents an individual carrier (disc) and its properties. It includes the function *process*.

Upon its initialisation, a class instance has a number of attributes. The most important ones of these are used by the *ppn.PPN.process* function (described above):

- divFileElements: list with *div* elements for all file-level structMap components (level 3 in [SIP specification](./sip-spec.md))
- fileElements: list with *file* elements for all files that are part of carrier
- techMDFileElements: list with file-level *techMD* elements
- premisCreationEvents: list with PREMIS imaging/ripping events (Isobuster/dBpoweramp logs)
- cdInfoElt: lxml element with serialized cd-info output

The above attributes are populated by the *carrier.Carrier.process* function, which is described below.

### Function *process*

Processes one carrier.

#### Input arguments

- SIPPath: SIP output directory
- sipFileCounterStart: start value of *sipFileCounter*
- counterTechMDStart: start value of *counterTechMD*

#### Processing steps

- Check if all expected files for this carrier exist, and do some additional consistency checks
- Read checksum file
- Verify checksum values
- Check for any files in carrier directory that sre not referenced in the checksum file
- Parse cd-info log and transform into serialized lxml element (using *cdinfo.parseCDInfoLog* function)
- Parse Isobuster report into lxml element
- Read Isobuster and/or dBpoweramp logs and put contents into PREMIS creation event (using *premis.addCreationEvent* function)
- Add all PREMIS creation events to *premisCreationEvents* list
- Create output directory for this carrier; then for each ISO image and/or audio file do the following (only if the *write* command is used):
    * Copy file to output directory
    * Do a post-copy checksum verification of the copied file
    * Create METS *file* element and *FLocat* subelement; set corresponding attributes
    * Create METS divisor element for *structMap*; set corresponding attributes
    * Add divisor element to *divFileElements* list
    * Create PREMIS *techMD* element with embedded PREMIS wrapper element
    * Generate PREMIS object info (using *premis.addObjectInstance* function)
    * Append PREMIS object info to *techMD* element
    * Add *techMD* element to *techMDFileElements* list
    * Add *file* element to *fileElements* list
    * Update counters
- Collect any errors and warnings that were encountered in the above steps

#### Output

The function returns updated values of the following variables:

- sipFileCounter: incremental counter of each file in the SIP
- counterTechMD: incremental counter for each *techMD* section in the SIP

## Module *premis*

This module contains functions for generating PREMIS creation events and object instances.

### Function *addCreationEvent*

Generates a PREMIS creation event from the log file of the creation application.

#### Input arguments

- log: path to log file (Isobuster, dBpoweramp)

#### Output

Element with PREMIS creation event.

### Function *addObjectInstance*

Generates a PREMIS object instance for a file. Apart from the standard PREMIS fields, this also includes the following external metadata (which are wrapped in *objectCharacteristicsExtension* subelements):

- Audio metadata in EBUCore format (only for audio files)
- Isobuster DFXML report (only for ISO/UDF/HFS+ etc. images)
- Isolyzer output (only for ISO/UDF/HFS+ etc. images)

#### Input arguments

- fileName
- fileSize
- mimeType
- sha512Sum
- sectorOffset
- isobusterReportElt

#### Output

Element with PREMIS object instance.

## Module *mdaudio*

Wrapper module for mediainfo, which is used for creating metadata for audio files in EBUCore format

### Function *getAudioMetadata*

Extracts metadata for an audio file.

#### Input arguments

- fileRef: path to audio file

#### Output

Dictionary with command-line, mediainfo exit status, EBUCore output as lxml Element and mediainfo stderr output.

## Module *cdinfo*

Module for reading and parsing cd-info output.

### Function *parseCDInfoLog*

This function reads a cd-info output file, and reprocesses it into lxml element, which can be reported as XML.

#### Input arguments

- fileCDInfo: cd-info output file

#### Output

- cdInfoElt: lxml element with serialized version of cd-info output
- dataTrackLSNStart: sector number (LSN) of data track (0 if no data track)

