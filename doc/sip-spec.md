# omSipCreator SIP specification

This document describes the structure of the SIPs created by *omSipCreator*, including its associated metadata.

## General structure of a SIP

Each SIP is represented as a directory. Each carrier that is part of the SIP is represented as a subdirectory within that directory. The SIP's root directory contains a [METS](https://www.loc.gov/mets/) file with technical, structural and bibliographic metadata. Bibliographic metadata is stored in [MODS](https://www.loc.gov/standards/mods/) format (3.4) which is embedded in a METS *mdWrap* element. Here's a simple example of a SIP that is made up of 2 carriers (which are represented as ISO 9660 images):


    ── 269448861
       ├── cd-rom
       │   ├── 1
       │   │   └── nuvoorstraks1.iso
       │   └── 2
       │       └── nuvoorstraks2.iso
       └── mets.xml

And here's an example of a SIP that contains 1 audio CD, with separate tracks represented as WAV files:

    ── 16385100X
       ├── cd-audio
       │   └── 1
       │       ├── track01.cdda.wav
       │       ├── track02.cdda.wav
       │       ├── track03.cdda.wav
       │       ├── track04.cdda.wav
       │       ├── track05.cdda.wav
       │       ├── track06.cdda.wav
       │       ├── track07.cdda.wav
       │       ├── track08.cdda.wav
       │       ├── track09.cdda.wav
       │       ├── track10.cdda.wav
       │       ├── track11.cdda.wav
       │       ├── track12.cdda.wav
       │       └── track13.cdda.wav
       └── mets.xml

## METS metadata

### dmdSec

- Contains top-level *mdWrap* element with the following attributes:
    - *MDTYPE* - indicates type of metadata that this element wraps. Value is *MODS*
    - *MDTYPEVERSION* - MODS version, is *3.4* (as per KB Metatadata policies)
- The *mdWrap* element contains one *xmlData* element
- The *xmlData* element contains one *mods* element.

The *mods* element contains the actual metadata elements. Most of these are imported from the KB catalogue record. Since the catalogue use Dublin Core (with some custom extensions), the DC elements are mapped to equivalent MODS elements. The mapping largely follows the [*Dublin Core Metadata Element Set Mapping to MODS Version 3*](http://www.loc.gov/standards/mods/dcsimple-mods.html) by Library of Congress. The table below shows each MODS element with its corresponding data source:

|MODS|Source|
|:--|:--|
|`titleInfo/title`|`dc:title@xsi:type="dcx:maintitle"` (catalogue)|
|`titleInfo/title`|`dc:title` (catalogue)|
|`name/namePart`; `name/role/roleTerm/@type="creator"`|`dc:creator` (catalogue)|
|`name/namePart`; `name/role/roleTerm/@type="contributor"`|`dc:contributor` (catalogue)|
|`originInfo@displayLabel="publisher"/publisher`|`dc:publisher` (catalogue)| 
|`originInfo/dateIssued`|`dc:date` (catalogue)|
|`subject/topic`|`dc:subject` (catalogue)|
|`typeOfResource`|mapping with *carrierType* (carrier metadata file)|
|`note`|`dcx:annotation` (catalogue)|
|`relatedItem/@type="host"/identifier/@type="ppn"`|*PPNParent* (carrier metadata file)|
|`relatedItem/@type="host"/identifier/@type="uri"`|`dc:identifier/@xsi:type="dcterms:URI"`(catalogue)|
|`relatedItem/@type="host"/identifier/@type="isbn"`|`dc:identifier/@xsi:type="dcterms:ISBN"` (catalogue)|

<!-- |`relatedItem/@type="host"/identifier/@type="uri"`|`dcx:recordIdentifier/@xsi:type="dcterms:URI"` (catalogue)| -->

Some additional notes to the above:

- Some of these elements (e.g. *creator* and *contributor*) may be repeatable.
- Title info in KB catalogue can either be in `dc:title@xsi:type="dcx:maintitle"`, `dc:title`, or both. If available,  `dc:title@xsi:type="dcx:maintitle"` is used as the mapping  source; otherwise  `dc:title` is used.
- The *relatedItem* element (with attribute *type* set to *host*) describes the relation of the intellectual entity with its (physical) parent item. It does this by referring to its identifiers in the KB catalogue.

### fileSec

- Contains one top-level *fileGrp* element (if a SIP spans multiple carriers, they are all wrapped inside the same *fileGrp* element).
- The *fileGrp* elements contains 1 or more *file* elements. Each *file* element has the following attributes:
    - *ID* - file identifier (e.g. *FILE_001*, *FILE_002*, etc.)
    - *SIZE* - file size in bytes
    - *MIMETYPE* - Mime type (e.g. *application/x-iso9660*)
    - *CHECKSUM*
    - *CHECKSUMTYPE* (*SHA-512*)
- Each *file* element contains an *FLocat* element with the following attributes:
    - *LOCTYPE* - Locator type. Value is *URL*
    - *xlink:href* - URL of file. Format: filepath, relative to root of SIP directory. Example:
        `xlink:href="file:///cd-rom/4/alles_over_bestandsformaten.iso"`

### structMap

- *structMap* contains a top-level *div* element with the following attributes:
    - *TYPE* - value *physical*
    - *LABEL* - value *volumes*
- Each carrier is wrapped into a *div* element that descibes the carrier using the following attributes:
    - *TYPE* - describes the carrier type. Possible values: *cd-rom*, *cd-audio*, *dvd-rom*, *dvd-video*
    - *ORDER* - in case of multiple carriers, this describes -for each *TYPE*, see above- the order of each volume 
- Each of the above *div* elements contains one or more further *div* elements that describe the components (files) that make up a carrier. They have the following attributes:
    - *TYPE* - describes the nature of the carrier component. Possible values are *disk image* and *audio track*.
    - *ORDER* - describes the order of each component (e.g. for an audio CD that is represented as multiple audio files, it describes the playing order).
- Finally each of the the above (file-level) *div* elements contains one *fptr*. It contains one *FILEID* attribute, whose value corresponds to the corresponding *ID* attribute in the *file* element (see *FileSec* description above).