
## About

OmSipCreator is a tool for converting batches of disk images (e.g. ISO 9660 CD-ROM images, raw floppy disk images, but also ripped audio files)  into SIPs that are ready for ingest in an archival system. This includes automatic generation of METS metadata files with structural and bibliographic metadata. Bibliographic metadata are extracted from the KB general catalogue (GGC), and converted to MODS format. OmSipCreator also performs various quality checks on the input batches.

Note that the metadata component in particular is specific to the situation and infrastructure at the KB. 

## Dependencies

You'll need [lxml](http://lxml.de/) to run this software.

## Usage

You can tell OmSipCreator what to do using either the *verify*  or *write* subcommands. 

### Verify a batch without writing any SIPs

    python omsipcreator.py verify batchIn

Here *batchIn* is the batch directory.

### Verify a batch and write SIPs
 
    python omsipcreator.py write batchIn dirOut

Here *dirOut* is the directory where the SIPs will be created. If *dirOut* is an existing directory, *all* of its contents will be overwritten! OmSipCreator will prompt you for confirmation if this happens:

    This will overwrite existing directory 'sipsOut' and remove its contents!
    Do you really want to proceed (Y/N)? > 

### Important: always *verify* before *write*

Always first run omSipCreator in *verify* mode. If this results in any reported errors, fix them first, since errors in the input batch are likely to result in output that is either unexpected or just plain wrong! Once no errors are reported, re-run the tool in *write* mode.

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
    │   ├── image1.iso
    │   └── image1.iso.md5
    └── s01d03
        ├── image2.iso
        └── image2.iso.md5


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

## SIP structure

Each SIP is represented as a directory. Each carrier that is part of the SIP is represented as a subdirectory within that directory. The SIP's root directory contains a [METS](https://www.loc.gov/mets/) file with technical, structural and bibliographic metadata. Bibliographic metadata is stored in [MODS](https://www.loc.gov/standards/mods/) format (3.4) which is embedded in a METS *mdWrap* element. Here's a simple example of a SIP that is made up of 2 carriers (which are represented as ISO 9660 images):
  

    ├── 1
    │   └── image1.iso
    ├── 2
    │   └── image2.iso
    └── mets.xml

And here's an example of a SIP that contains 1 audio CD, with separate tracks represented as WAV files:

    ├── 1
    │   ├── track01.cdda.wav
    │   ├── track02.cdda.wav
    │   ├── ...
    │   ├── ...
    │   ├── track12.cdda.wav
    │   └── track13.cdda.wav
    └── mets.xml

### METS metadata

To be written.
    
## Quality checks

When run in either *verify* or *write* mode, omSipCreator performs a number checks on the input batch. Each of he following checks will result in an *error* in case of failure:

- Does batch directory exist?
- Does carrier metadata file exist?
- Can carrier metadata file be opened and is it parsable?
- Does carrier metadata file contain exactly 1 instance of each mandatory column?
- Does each *imagePath* entry point to an existing directory?
- Is each *volumeNumber* entry an integer value?
- Is each *carrierType* entry a permitted value (check against controlled vocabulary)?
- Are all values of *IPIdentifierParent* within one intellectual entity identical?
- Are all values of *imagePath* within the carrier metadata file unique (no duplicate values)?
- Are all instances of *volumeNumber* within an intellectual entity unique?
- Are all instances of *carrierType*  within an intellectual entity identical?
- Are all directories within the batch referenced in the carrier metadata file (by way of *imagePath*)?
- Does each carrier directory (i.e. *imagePath*) contain exactly 1 MD5 checksum file (identified by *.md5* file extension)?
- For each entry in the checksum file, is the MD5 checksum identical to the re-calculated checksum for that file?
- Does a carrier directory contain any files that are not referenced in the checksum file?
- Does a search for *IPIdentifierParent* in the GGC catalogue result in exactly 1 matching record? 

In *write* mode omSipCreator performs the following additional checks:

- Is the output directory a writable location?
- Could a SIP directory be created for the current IP?
- Could a carrier directory be created for the current SIP?  
- Could the image file(s) for the current carrier be copied to its SIP carrier directory?
- Does the MD5 checksum of each copied image file match the original checksum (post-copy checksum verification)?

Finally, omSipcreator will report a *warning* in the following situations:

- Lower value of *volumeNumber* within an intellectual entity is not equal to 1.
- Values of *volumeNumber* within an intellectual entity are not consecutive numbers.

Both situations may indicate a data entry error, but they may also reflect that the physical carriers are simply missing.


## Contributors

Written by Johan van der Knijff, except *sru.py* which was adapted from the [KB Python API](https://github.com/KBNLresearch/KB-python-API) which is written by WillemJan Faber. The KB Python API is released under the GNU GENERAL PUBLIC LICENSE.

