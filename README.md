
## About

OmSipCreator is a tool for converting batches of disk images (e.g. ISO 9660 CD-ROM images, raw floppy disk images, but also ripped audio files)  into SIPs that are ready for ingest in an archival system. This includes automatic generation of METS metadata files with structural and bibliographic metadata. Bibliographic Metadata are extracted from the KB general catalogue (GGC), and converted to MODS format. OmSipCreator also performs various quality checks on the input batches.

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


## Structure of SIP

## Quality checks

## Contributors

Written by Johan van der Knijff, except *sru.py* which was adapted from the [KB Python API](https://github.com/KBNLresearch/KB-python-API) which is written by WillemJan Faber. The KB Python API is released under the GNU GENERAL PUBLIC LICENSE.

