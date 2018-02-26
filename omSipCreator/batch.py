#! /usr/bin/env python
"""
Class and processing functions for one bATCH
"""

import os
import sys
import shutil
import csv
import logging
from operator import itemgetter
from itertools import groupby
from lxml import etree
from . import config
from .ppn import PPN
from .shared import errorExit

def get_immediate_subdirectories(a_dir, ignoreDirs):
    """Returns list of immediate subdirectories
    Directories that end with suffixes defined by ignoreDirs are ignored
    """
    subDirs = []
    for root, dirs, files in os.walk(a_dir):
        for myDir in dirs:
            ignore = False
            for ignoreDir in ignoreDirs:
                if myDir.endswith(ignoreDir):
                    ignore = True
            if not ignore:
                subDirs.append(os.path.abspath(os.path.join(root, myDir)))

    return subDirs


# PPN class

class Batch:
    """Batch class"""
    def __init__(self, batchDir):
        """initialise Batch class instance"""

        # Batch directory (full path)
        self.batchDir = batchDir
        # Name of batch manifest file
        self.fileBatchManifest = "manifest.csv"
        # Name of batch log file
        self.fileBatchLog = "batch.log"
        # List with batch manifest header items
        self.headerBatchManifest = []
        # List with batch manifest row items
        self.rowsBatchManifest = []
        # Dictionary with, for each batch manifest header field,
        # the corresponding column number
        self.colsBatchManifest = {}

        # Header values of mandatory columns in batch manifest
        self.requiredColsBatchManifest = ['jobID',
                                     'PPN',
                                     'volumeNo',
                                     'carrierType',
                                     'title',
                                     'volumeID',
                                     'success',
                                     'containsAudio',
                                     'containsData',
                                     'cdExtra']

        # List for storing directories as extracted from batch manifest
        config.dirsInMetaCarriers = []


    def process(self):

        """Process a batch"""

        # Check if batch dir exists
        if not os.path.isdir(self.batchDir):
            logging.fatal("input batch directory does not exist")
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Get listing of all directories (not files) in batch dir (used later for completeness check)
        # Note: all entries as full, absolute file paths!

        # Define dirs to ignore (jobs and jobsFailed)
        ignoreDirs = ["jobs", "jobsFailed"]

        dirsInBatch = get_immediate_subdirectories(self.batchDir, ignoreDirs)

        # Check if batch manifest exists
        self.batchManifest = os.path.join(self.batchDir, self.fileBatchManifest)
        if not os.path.isfile(self.batchManifest):
            logging.fatal("file " + self.batchManifest + " does not exist")
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Read batch manifest as CSV and import header and
        # row data to 2 separate lists
        try:
            if sys.version.startswith('3'):
                # Py3: csv.reader expects file opened in text mode
                fBatchManifest = open(self.batchManifest, "r", encoding="utf-8")
            elif sys.version.startswith('2'):
                # Py2: csv.reader expects file opened in binary mode
                fBatchManifest = open(self.batchManifest, "rb")
            batchManifestCSV = csv.reader(fBatchManifest)
            self.headerBatchManifest = next(batchManifestCSV)
            self.rowsBatchManifest = [row for row in batchManifestCSV]
            fBatchManifest.close()
        except IOError:
            logging.fatal("cannot read " + self.batchManifest)
            config.errors += 1
            errorExit(config.errors, config.warnings)
        except csv.Error:
            logging.fatal("error parsing " + self.batchManifest)
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Iterate over rows and check that number of columns
        # corresponds to number of header columns.
        # Remove any empty list elements (e.g. due to EOL chars)
        # to avoid trouble with itemgetter

        colsHeader = len(self.headerBatchManifest)

        rowCount = 1
        for row in self.rowsBatchManifest:
            rowCount += 1
            colsRow = len(row)
            if colsRow == 0:
                self.rowsBatchManifest.remove(row)
            elif colsRow != colsHeader:
                logging.fatal("wrong number of columns in row " +
                              str(rowCount) + " of '" + self.batchManifest + "'")
                config.errors += 1
                errorExit(config.errors, config.warnings)

        # Create output directory if in SIP creation mode
        if config.createSIPs:
            # Remove output dir tree if it exists already
            # Potentially dangerous, so ask for user confirmation
            if os.path.isdir(config.dirOut):

                config.out.write("This will overwrite existing directory '" + config.dirOut +
                          "' and remove its contents!\nDo you really want to proceed (Y/N)? > ")
                response = input()

                if response.upper() == "Y":
                    try:
                        shutil.rmtree(config.dirOut)
                    except OSError:
                        logging.fatal("cannot remove '" + dirOut + "'")
                        config.errors += 1
                        errorExit(config.errors, config.warnings)

            # Create new dir
            try:
                os.makedirs(config.dirOut)
            except OSError:
                logging.fatal("cannot create '" + config.dirOut + "'")
                config.errors += 1
                errorExit(config.errors, config.warnings)

        # ********
        # ** Process batch manifest **
        # ********

        # Check that there is exactly one occurrence of each mandatory column

        for requiredCol in self.requiredColsBatchManifest:
            occurs = self.headerBatchManifest.count(requiredCol)
            if occurs != 1:
                logging.fatal("found " + str(occurs) + " occurrences of column '" +
                              requiredCol + "' in " + self.batchManifest + " (expected 1)")
                config.errors += 1
                # No point in continuing if we end up here ...
                errorExit(config.errors, config.warnings)

        # Populate dictionary that gives for each header field the corresponding column number

        col = 0
        for header in self.headerBatchManifest:
            self.colsBatchManifest[header] = col
            col += 1

        # Sort rows by PPN
        self.rowsBatchManifest.sort(key=itemgetter(1))

        # Group by PPN
        metaCarriersByPPN = groupby(self.rowsBatchManifest, itemgetter(1))

        # ********
        # ** Iterate over PPNs**
        # ********

        for PPNValue, carriers in metaCarriersByPPN:
            logging.info("Processing PPN " + PPNValue)
            # Create PPN class instance for this PPN
            thisPPN = PPN(PPNValue)
            # Call PPN processing function
            thisPPN.process(carriers, self.batchDir, self.colsBatchManifest)

        # Check if directories that are part of batch are all represented in carrier metadata file
        # (reverse already covered by checks above)

        # Diff as list
        diffDirs = list(set(dirsInBatch) - set(config.dirsInMetaCarriers))

        # Report each item in list as an error

        for directory in diffDirs:
            logging.error("PPN " + PPN + ": directory '" + directory +
                          "' not referenced in '" + self.batchManifest + "'")
            config.errors += 1
            config.failedPPNs.append(PPN)

        # Summarise no. of warnings / errors
        logging.info("Verify / write resulted in " + str(config.errors) +
                     " errors and " + str(config.warnings) + " warnings")

        # Reset warnings/errors
        config.errors = 0
        config.warnings = 0

        # Get all unique values in failedPPNs by converting to a set (and then back to a list)
        config.failedPPNs = (list(set(config.failedPPNs)))

        # Start pruning if prune command was issued
        if config.pruneBatch and config.failedPPNs != []:
            pruneBatch()


