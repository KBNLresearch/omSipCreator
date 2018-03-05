#! /usr/bin/env python
"""
SIP Creator for Offline Media Images.
"""

import sys
import os
import imp
import argparse
import logging
from . import config
from .batch import Batch

# Bind raw_input (Python 3) to input (Python 2)
# Source: http://stackoverflow.com/a/21731110/1209004
try:
    input = raw_input
except NameError:
    pass


# Script name
config.scriptPath, config.scriptName = os.path.split(sys.argv[0])

# scriptName is empty when called from Java/Jython, so this needs a fix
if len(config.scriptName) == 0:
    config.scriptName = 'omSipCreator'

__version__ = "0.6.0"
config.version = __version__

# Create parser
parser = argparse.ArgumentParser(
    description="SIP Creator for Offline Media Images")


def main_is_frozen():
    """Returns True if maijn function is frozen
    (e.g. PyInstaller/Py2Exe executable)
    """
    return (hasattr(sys, "frozen") or  # new py2exe
            hasattr(sys, "importers") or  # old py2exe
            imp.is_frozen("__main__"))  # tools/freeze


def get_main_dir():
    """Reurns installation directory"""
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])


def checkFileExists(fileIn):
    """Check if file exists and exit if not"""
    if not os.path.isfile(fileIn):
        msg = "file " + fileIn + " does not exist!"
        sys.stderr.write("Error: " + msg + "\n")
        sys.exit()


def parseCommandLine():
    """Parse command-line arguments"""

    # Sub-parsers for check and write commands

    subparsers = parser.add_subparsers(help='sub-command help',
                                       dest='subcommand')
    parser_verify = subparsers.add_parser('verify',
                                          help='only verify input batch without writing SIPs')

    parser_verify.add_argument('batchIn',
                               action="store",
                               type=str,
                               help="input batch")

    parser_verify.add_argument('--nochecksums', '-n',
                               action='store_true',
                               dest='skipChecksumFlag',
                               default=False,
                               help="skip checksum verification")

    parser_prune = subparsers.add_parser('prune',
                                         help="verify input batch, then write 'pruned' version \
                         of batch that omits all PPNs that have errors. Write PPNs with \
                         errors to a separate batch.")

    parser_prune.add_argument('batchIn',
                              action="store",
                              type=str,
                              help="input batch")

    parser_prune.add_argument('batchErr',
                              action="store",
                              type=str,
                              help="name of batch that will contain all PPNs with errors")

    parser_write = subparsers.add_parser('write',
                                         help="verify input batch and write SIPs. Before using \
                         'write' first run the 'verify' command and fix any reported errors.")

    parser_write.add_argument('batchIn',
                              action="store",
                              type=str,
                              help="input batch")

    parser_write.add_argument('dirOut',
                              action="store",
                              type=str,
                              help="output directory where SIPs are written")

    parser.add_argument('--version', '-v',
                        action='version',
                        version=__version__)

    # Parse arguments
    args = parser.parse_args()

    return args


def printHelpAndExit():
    """Print usage message and exit"""
    print('')
    parser.print_help()
    sys.exit()


def main():
    """Main CLI function"""

    # Set up logger; suppress info messages from requests module
    logging.getLogger("requests").setLevel(logging.WARNING)
    logFormatter = logging.Formatter('%(levelname)s - %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)

    # Controlled vocabulary for 'carrierType' field
    config.carrierTypeAllowedValues = ['cd-rom',
                                       'cd-audio',
                                       'dvd-rom',
                                       'dvd-video']

    # Define name spaces for METS output
    config.mets_ns = 'http://www.loc.gov/METS/'
    config.mods_ns = 'http://www.loc.gov/mods/v3'
    config.premis_ns = 'http://www.loc.gov/premis/v3'
    config.ebucore_ns = 'urn:ebu:metadata-schema:ebucore'
    config.isolyzer_ns = 'https://github.com/KBNLresearch/isolyzer'
    config.cdInfo_ns = 'https://www.gnu.org/software/libcdio/libcdio.html#cd_002dinfo'  # TODO: is this a proper namespace?
    config.dfxml_ns = 'http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML'
    config.xlink_ns = 'http://www.w3.org/1999/xlink'
    config.xsi_ns = 'http://www.w3.org/2001/XMLSchema-instance'
    config.metsSchema = 'http://www.loc.gov/METS/ http://www.loc.gov/standards/mets/mets.xsd'
    config.modsSchema = 'http://www.loc.gov/mods/v3 https://www.loc.gov/standards/mods/v3/mods-3-4.xsd'
    config.premisSchema = 'http://www.loc.gov/premis/v3 https://www.loc.gov/standards/premis/premis.xsd'
    config.ebucoreSchema = 'https://raw.githubusercontent.com/ebu/ebucore/master/ebucore.xsd'

    config.NSMAP = {"mets": config.mets_ns,
                    "mods": config.mods_ns,
                    "premis": config.premis_ns,
                    "ebucore": config.ebucore_ns,
                    "isolyzer": config.isolyzer_ns,
                    "cd-info": config.cdInfo_ns,
                    "dfxml": config.dfxml_ns,
                    "xlink": config.xlink_ns,
                    "xsi": config.xsi_ns}

    # Counters for number of errors and warnings
    config.errors = 0
    config.warnings = 0

    # List for storing failed PPN values (needed for pruning)
    config.failedPPNs = []

    # Flag that indicates if SIPs will be written
    config.createSIPs = False

    # Flag that indicates if prune option is used
    config.pruneBatch = False

    # Flag that indicates if checksum checking is skipped (prune mode only!)
    config.skipChecksumFlag = False

    # Get input from command line
    args = parseCommandLine()
    action = args.subcommand
    if action is None:
        # Exit and print help message if command line is empty
        printHelpAndExit()

    batchDir = os.path.normpath(args.batchIn)

    if action == "verify":
        config.skipChecksumFlag = args.skipChecksumFlag
    elif action == "write":
        config.dirOut = os.path.normpath(args.dirOut)
        config.createSIPs = True
    elif action == "prune":
        config.batchErr = os.path.normpath(args.batchErr)
        config.dirOut = None
        config.pruneBatch = True
    else:
        # Dummy value
        config.dirOut = None

    # Locate package directory
    packageDir = os.path.dirname(os.path.abspath(__file__))
    # Tools directory
    toolsDirUser = os.path.join(packageDir, 'tools')

    # Path to MediaInfo
    if sys.platform == "win32":
        config.mediaInfoExe = os.path.join(
            toolsDirUser, 'mediainfo', 'MediaInfo.exe')
    elif sys.platform in ["linux", "linux2"]:
        config.mediaInfoExe = "/usr/bin/mediainfo"
    checkFileExists(config.mediaInfoExe)

    # Create Batch instance
    thisBatch = Batch(batchDir)

    # Process batch
    thisBatch.process()

    # Start pruning if prune command was issued
    if config.pruneBatch and config.failedPPNs != []:
        thisBatch.prune()


if __name__ == "__main__":
    main()
