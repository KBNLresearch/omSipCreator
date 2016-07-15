
## About

OmSipCreator is a tool for converting batches of disk images (e.g. ISO 9660 CD-ROM images, raw floppy disk images, but also ripped audio files)  into SIPs that are ready for ingest in an archival system. This includes automatic generation of METS metadata files with structural and bibliographic metadata. Bibliographic metadata are extracted from the KB general catalogue (GGC), and converted to MODS format. OmSipCreator also performs various quality checks on the input batches.

Note that the metadata component in particular is specific to the situation and infrastructure at the KB. 

## Dependencies

You'll need [lxml](http://lxml.de/) to run this software.

## Usage

You can tell OmSIPCreator what to do using either the *verify*  or *write* subcommands. 

### Verify a batch without writing any SIPs

    python omsipcreator.py verify batchIn

Here *batchIn* is the batch directory.

### Verify a batch and write SIPs
 
    python omsipcreator.py write batchIn dirOut

Here *dirOut* is the directory where the SIPs will be created. If *dirOut* is an existing directory, *all* of its contents will be overwritten! OmSipCreator will prompt you for confirmation if this happens:

    This will overwrite existing directory 'sipsOut' and remove its contents!
    Do you really want to proceed (Y/N)? > 

## Structure of input batch

The input batch is simply a directory that contains a number of subdirectories, each of which represents exactly one data carrier. Furthermore it contains a comma-delimited text file with basic metadata about each carrier. The diagram below shows an example of a batch that contains 3 carriers.


    ├── metacarriers.csv
    ├── s01d01
    │   ├── track01.cdda.wav
    │   ├── track02.cdda.wav
    │   ├── ...
    │   ├── ...
    │   ├── track13.cdda.wav
    │   └── tracks.md5
    ├── s01d02
    │   ├── alles_over_bestandsformaten.iso
    │   └── alles_over_bestandsformaten.iso.md5
    └── s01d03
        ├── birds_of_tropical_asia_2.iso
        └── birds_of_tropical_asia_2.iso.md5


### Carrier directory structure

Each carrier directory contains:

1. One or more files that represent the data carrier. This is typically an ISO 9660 image, but for an audio CD with multiple tracks this can also be multiple audio (e.g. WAV) files. In the latter case, it is important that the original playing order can be inferred from the file names. In other words, sorting the file names in ascending order should reproduce the original playing order. Note that (nearly?) all audio CD ripping software does this by default.
2. Exactly one checksum file that contains the MD5 checksums of all files in the directory. The name of the checksum file must end with the extension *.md5* (other than that its name doesn't matter). Each line in the file has the following format:

        checksum filename

    Both fields are separated by 1 or more spaces. the *filename* field should not include any file path information. Here's an example:
    
        67dfc7f5b63df9cd4c6add729fa407fe  track01.cdda.wav
        27f898419a912d5327188ccf2ad7ccce  track02.cdda.wav
        4185467fc835b931af18a15c7cc5ffcc  track03.cdda.wav

### Carrier metadata file format

The carrier metadata file is a comma-delimited text file with the name *metacarriers.csv*. The first line is a header line: 

    IPIdentifier,IPIdentifierParent,imagePath,volumeNumber,carrierType
    
Each of the remaining lines represents one carrier, for which it contains the following fields:

1. *IPIdentifier* - this is an identifier that uniquely identifies (within the current batch) the intellectual entity to which this carrier belongs. For example, if a set of CD-ROMs span 3 volumes, each carrier (volume) in this set must have the same value for *IPIdentifier*. This allows OmSipCreator to figure out that all volumes belong to the same entity.
2. *IPIdentifierParent* - identifier of the physical item in the KB Collection to which this item belongs. For the KB case this is the PPN identifier in the KB catalogue (GGC).
3. *imagePath* - file path to to the directory where the image file(s) of this carrier are stored. Must be defined relative to the batch directory (no absolute paths!).
4. *volumeNumber* - for intellectual entities that span multiple carriers, this defines the volume number (1 for single-volume items).  
5. *carrierType* - code that specifies the carrier type. Currently the following values are permitted (most likely this will be extended later):
    - cd-rom
    - dvd-rom
    - cd-audio
    - dvd-video

Below is a simple example of carrier metadata file:

    IPIdentifier,IPIdentifierParent,imagePath,volumeNumber,carrierType
    1,121274306,./s01d01/,1,cd-audio
    2,155658050,./s01d02/,1,cd-rom
    3,236599380,./s01d03/,1,cd-rom
    2,155658050,./s01d04/,2,cd-rom

In the above example the second and fourth carriers are both part of a 2-volume item. Consequently the *IPIdentifier* values of both carriers are identical.


## Structure of SIP

## Quality checks

## Contributors

Written by Johan van der Knijff, except *sru.py* which was adapted from the [KB Python API](https://github.com/KBNLresearch/KB-python-API) which is written by WillemJan Faber. The KB Python API is released under the GNU GENERAL PUBLIC LICENSE.

