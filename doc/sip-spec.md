# omSipCreator SIP specification

This document describes the structure of the SIPs created by *omSipCreator*, including its associated metadata.

## General structure of a SIP

Each SIP is represented as a directory. Each carrier that is part of the SIP is represented as a subdirectory within that directory. The SIP's root directory contains a [METS](https://www.loc.gov/mets/) file with technical, structural and bibliographic metadata. Here's a simple example of a SIP that is made up of 2 carriers (which are represented as ISO 9660 images):


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

The METS file contains various types of metadata. Here's an overview:

- Bibliographic metadata, which are stored in [MODS](https://www.loc.gov/standards/mods/) format (3.4).
- Carrier-level technical metadata in the form of XML-serialized output of the [cd-info](https://www.gnu.org/software/libcdio/libcdio.html#cd_002dinfo) tool.
- File-level technical metadata. Each file (ISO image, audio file) has an associated METS *techMD* section that wraps around a [PREMIS](https://www.loc.gov/standards/premis/) *Object*. The PREMIS *objectCharacteristicsExtension* unit is used to wrap additional, format-specific metadata that are not covered by the PREMIS semantic units:
    * An [Isobuster DFXML report](https://www.isobuster.com/dfxml-example.php) that contains, amongst other things, a listing of all files inside the image (only for ISO/HFS/UDF images).
    * Output of the [Isolyzer](https://github.com/KBNLresearch/isolyzer) tool, which provides information about the file systems used inside the image (only for  ISO/HFS/UDF images).
    * Descriptive and technical metadata on audio files in [EBUCore](https://tech.ebu.ch/MetadataEbuCore) format (only for audio files).
- Event metadata about the imaging/ripping process (IsoBuster exit status, dBpoweramp log), which are wrapped in a *digiprovMD* element.
- Basic file-level metadata (METS *fileSec*).
- Structural metadata (METS *structMap*).

The following sections describe each of the above elements in more detail.

### METS root

The METS root element has the following namespace declarations:

- `xmlns:mets="http://www.loc.gov/METS/"`
- `xmlns:mods="http://www.loc.gov/mods/v3"`
- `xmlns:premis="http://www.loc.gov/premis/v3"`
- `xmlns:ebucore="urn:ebu:metadata-schema:ebucore"`
- `xmlns:isolyzer="https://github.com/KBNLresearch/isolyzer"`
- `xmlns:cd-info="https://www.gnu.org/software/libcdio/libcdio.html#cd_002dinfo"`
- `xmlns:dfxml="http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML"`
- `xmlns:xlink="http://www.w3.org/1999/xlink"`
- `xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"`

It also has the following schema references:

- `xsi:schemaLocation="http://www.loc.gov/METS/ http://www.loc.gov/standards/mets/mets.xsd http://www.loc.gov/mods/v3 https://www.loc.gov/standards/mods/v3/mods-3-4.xsd http://www.loc.gov/premis/v3 https://www.loc.gov/standards/premis/premis.xsd"`

Finally it has the following attribute:

- `@TYPE="SIP"`

The METS root element contains the following sub-elements:

- *dmdSec*
- *amdSec*
- *fileSec*
- *structMap*

These are all described in the following sections.

### METS dmdSec

The *dmdSec* element has the following attribute:

- `@ID=dmdSec_x`

Here, *x* is an index.

The *dmdSec* element contains an *mdWrap* element with the following attributes:

- `@MDTYPE="MODS"`
- `@MDTYPEVERSION="3.4"` (as per KB Metatadata policies)

The *mdWrap* element contains an *xmlData* element, which in turn holds a *mods* element.

### MODS

The *mods* element contains descriptive and bibliographic metadata, most of which are imported from the KB catalogue record. Since the catalogue use Dublin Cores (with some custom extensions), the DC elements are mapped to equivalent MODS elements. The mapping largely follows the [*Dublin Core Metadata Element Set Mapping to MODS Version 3*](http://www.loc.gov/standards/mods/dcsimple-mods.html) by Library of Congress. The table below shows each MODS element with its corresponding data source:

|MODS|Source|
|:--|:--|
|`mods/titleInfo/title`|`dc:title@xsi:type="dcx:maintitle"` (catalogue)|
|`mods/titleInfo/title`|`dc:title` (catalogue)|
|`mods/name/namePart`; `name/role/roleTerm/@type="creator"`|`dc:creator` (catalogue)|
|`mods/name/namePart`; `name/role/roleTerm/@type="contributor"`|`dc:contributor` (catalogue)|
|`mods/originInfo@displayLabel="publisher"/publisher`|`dc:publisher` (catalogue)|
|`mods/originInfo/dateIssued`|`dc:date` (catalogue)|
|`mods/subject/topic`|`dc:subject` (catalogue)|
|`mods/typeOfResource`|mapping with *carrierType* field from batch manifest|
|`mods/note`|`dcx:annotation` (catalogue)|
|`mods/relatedItem/@type="host"/identifier/@type="ppn"`|*PPN* field from batch manifest|
|`mods/relatedItem/@type="host"/identifier/@type="uri"`|`dc:identifier/@xsi:type="dcterms:URI"`(catalogue)|
|`mods/relatedItem/@type="host"/identifier/@type="isbn"`|`dc:identifier/@xsi:type="dcterms:ISBN"` (catalogue)|
|`mods/recordInfo/recordOrigin`|Text string generated by omSipCreator (e.g. "Automatically generated by omSipCreator.py v. 0.4.11 from records in KB Catalogue.")|

Some notes to the above:

- Some of these elements (e.g. *creator* and *contributor*) may be repeatable.
- Title info in KB catalogue can either be in `dc:title@xsi:type="dcx:maintitle"`, `dc:title`, or both. If available,  `dc:title@xsi:type="dcx:maintitle"` is used as the mapping  source; otherwise  `dc:title` is used.
- The *relatedItem* element (with attribute *type* set to *host*) describes the relation of the intellectual entity with its (physical) parent item. It does this by referring to its identifiers in the KB catalogue.

### METS amdSec

The *amdSec* element has the following attribute:

- `@ID=amdSec_x`

Here, *x* is an index.

The *amdSec* element contains one or more *techMD* sections, and one or more *digiprovMD* sections. These are described below.

### METS techMD, carrier level

This element contains carrier-level technical metadata in the form of XML-serialized output of the [cd-info](https://www.gnu.org/software/libcdio/libcdio.html#cd_002dinfo) tool.

The *techMD* element has the following attribute:

- `@ID=techMD_x`

Here, *x* is an index.

The *techMD* element contains a METS *mdWrap* element with the following attributes:

- `@MIMETYPE="text/xml"`
- `@MDTYPE="OTHER"`
- `@OTHERMDTYPE="cd-info output"`

Inside the *mdWrap* element is a METS *xmlData* element, which in turn wraps a *cd-info* element (which is declared in the *cd-info* namespace). The following table lists all subelements of *cd-info*:

|Element|Description|
|:--|:--|
|`cd-info/trackList`|Holds the track list|
|`cd-info/trackList/track`|Holds all properties of one track (repeated for each track)|
|`cd-info/trackList/track/trackNumber`|Track number|
|`cd-info/trackList/track/MSF`|Track start position timecode [minutes:seconds:frames]|
|`cd-info/trackList/track/LSN`|Track start position sector offset [number of 2048-byte sectors]|
|`cd-info/trackList/track/type`|Track type [audio/data/leadout]|
|`cd-info/analysisReport`|Holds the full analysis report, and three *True*/*False* flags that are derived from it|
|`cd-info/analysisReport/cdExtra`|Flag that is *True* if carrier is a [CD-Extra / Blue Book](https://en.wikipedia.org/wiki/Blue_Book_(CD_standard)) disc, and *False* otherwise|
|`cd-info/analysisReport/multiSession`|Flag that is *True* if carrier is a multisession disc, and *False* otherwise|
|`cd-info/analysisReport/mixedMode`|Flag that is *True* if carrier is a [mixed mode](https://en.wikipedia.org/wiki/Mixed_Mode_CD) disc, and *False* otherwise|
|`cd-info/analysisReport/fullReport`|Contains full analysis report as unstructured text|

Note that, unlike the file-level technical metadata (see next section), the carrier-level metadata are *not* wrapped inside a PREMIS *objectCharacteristicsExtension* element. The reason for this is that PREMIS *only* allows *objectCharacteristicsExtension* to be used for File and Bitstream objects, and not for Intellectual Entity / Representation objects. See also: [*How/where to store metadata about optical media sector layout in METS/PREMIS*](http://qanda.digipres.org/1146/where-store-metadata-about-optical-media-sector-layout-premis).


### METS techMD, file level

This element contains file-level technical metadata for one file. The *techMD* element has the following attribute:

- `@ID=techMD_x`

Here, *x* is an index.

The *techMD* element contains a METS *mdWrap* element with the following attributes:

- `@MIMETYPE="text/xml"`
- `@MDTYPE="PREMIS:OBJECT"`
- `@MDTYPEVERSION="3.0"`

Inside the *mdWrap* element is a METS *xmlData* element, which in turn wraps a [PREMIS](https://www.loc.gov/standards/premis/) *object* element (which is declared in the *premis* namespace). It has the following attribute:

- `@xsi:type=premis:file`

The following table lists all subelements of the PREMIS *object*:

|Element|Description|
|:--|:--|
|`object/objectIdentifier/objectIdentifierType`|value *UUID*|
|`object/objectIdentifier/objectIdentifierValue`|Automatically generated UUID identifier|
|`object/objectCharacteristics/compositionLevel`|value *0*|
|`object/objectCharacteristics/fixity/messageDigestAlgorithm`|value *SHA-512*|
|`object/objectCharacteristics/fixity/messageDigest`|value of computed SHA-512 hash|
|`object/objectCharacteristics/fixity/messageDigestOriginator`|value *python.hashlib.sha512.hexdigest*|
|`object/objectCharacteristics/size`|File size|
|`object/objectCharacteristics/format/formatDesignation/formatName`|either *ISO_Image*, *Wave* or *FLAC*|
|`object/objectCharacteristics/format/formatDesignation/formatRegistry/formatRegistryName`|value *DIAS*|
|`object/objectCharacteristics/format/formatDesignation/formatRegistry/formatRegistryKey`|value *n/a* **TODO**: figure how out to use the *formatRegistry* elements!|
|`object/objectCharacteristics/objectCharacteristicsExtension`|used to wrap additional format-specific metadata (see below)|

### Use of objectCharacteristicsExtension element

The *objectCharacteristicsExtension* element is used to wrap additional format-specific metadata. For an ISO image, there are 2 *objectCharacteristicsExtension* elements:

- The first one holds an [*Isobuster* report](https://www.isobuster.com/dfxml-example.php) in [DFXML](http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML) (Digital Forensics XML) format. The DFXML report contains, amongst other things, a listing of all files inside the ISO image.
- The second one contains the output of the [*Isolyzer*](https://github.com/KBNLresearch/isolyzer) tool. This contains information about the file system(s) used inside the image (only for  ISO/HFS/UDF images).

For an audio file (FLAC or Wave format) only one *objectCharacteristicsExtension* element is written. In this case it contains descriptive and technical audio-specific metadata that were extracted using the [*MediaInfo*](https://mediaarea.net/en/MediaInfo) tool in [EBUCore](https://tech.ebu.ch/MetadataEbuCore) format.

Note: for now the choice for the EBUCore format is provisional. The main reason it was chose here is the fact that EBUCore is natively supported by MediaInfo, which makes implementing it trivially simple.

### METS digiprovMD

This element contains event metadata. The *digiprovMD* element has the following attribute:

- `@ID=digiprovMD_x`

Here, *x* is an index.

The *digiprovMD* element contains a METS *mdWrap* element with the following attributes:

- `@MIMETYPE="text/xml"`
- `@MDTYPE="PREMIS:EVENT"`
- `@MDTYPEVERSION="3.0"`

Inside the *mdWrap* element is a METS *xmlData* element, which in turn wraps a PREMIS *event* element (which is declared in the *premis* namespace).

The following table lists all subelements of the PREMIS *event*:

|Element|Description|
|:--|:--|
|`event/eventIdentifier/eventIdentifierType`|value *UUID*|
|`event/eventIdentifier/eventIdentifierValue`|Automatically generated UUID identifier|

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