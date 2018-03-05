#! /usr/bin/env python
"""
Class and processing functions for one batch
"""

import os
import sys
import shutil
import glob
import csv
import logging
from operator import itemgetter
from itertools import groupby
from . import config
from . import checksums
from .ppn import PPN
from .shared import errorExit
from .shared import get_immediate_subdirectories


class Batch:
    """Batch class"""
    def __init__(self, batchDir):
        """initialise Batch class instance"""

        # Batch directory (full path)
        self.batchDir = batchDir
        # Name of batch manifest file
        self.fileBatchManifest = "manifest.csv"
        # Batch manifest (full path)
        self.batchManifest = os.path.join(self.batchDir, self.fileBatchManifest)
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

        # Define dirs to ignore (jobs and jobsFailed)
        ignoreDirs = ["jobs", "jobsFailed"]

        # Get listing of all directories (not files) in batch dir (used later for
        # completeness check)
        # Note: all entries as full, absolute file paths!

        dirsInBatch = get_immediate_subdirectories(self.batchDir, ignoreDirs)

        # Check if batch manifest exists
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
                                 "' and remove its contents!\nDo you really want to proceed" +
                                 " (Y/N)? > ")
                response = input()

                if response.upper() == "Y":
                    try:
                        shutil.rmtree(config.dirOut)
                    except OSError:
                        logging.fatal("cannot remove '" + config.dirOut + "'")
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

    def prune(self):
        """Prune batch"""

        logging.info("Start pruning")

        # Check if batchErr is an existing directory. If yes,
        # prompt user to confirm that it will be overwritten

        if os.path.isdir(config.batchErr):

            config.out.write("\nThis will overwrite existing directory '" +
                             config.batchErr + "' and remove its contents!\n" +
                             "Do you really want to proceed (Y/N)? > ")
            response = input()

            if response.upper() == "Y":
                try:
                    shutil.rmtree(config.batchErr)
                except OSError:
                    logging.fatal("cannot remove '" + config.batchErr + "'")
                    config.errors += 1
                    errorExit(config.errors, config.warnings)
            else:
                logging.error("exiting because user pressed 'N'")
                errorExit(config.errors, config.warnings)

        # Create batchErr directory

        try:
            os.makedirs(config.batchErr)
        except (OSError, IOError):
            logging.fatal("Cannot create directory '" + config.batchErr + "'")
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Add batch manifest to batchErr directory
        batchManifestErr = os.path.join(config.batchErr, self.fileBatchManifest)

        # Add temporary (updated) batch manifest to batchIn
        fileBatchManifestTemp = "tmp.csv"
        batchManifestTemp = os.path.join(self.batchDir, fileBatchManifestTemp)

        try:
            if sys.version.startswith('3'):
                # Py3: csv.reader expects file opened in text mode
                fbatchManifestErr = open(
                    batchManifestErr, "w", encoding="utf-8")
                fbatchManifestTemp = open(
                    batchManifestTemp, "w", encoding="utf-8")
            elif sys.version.startswith('2'):
                # Py2: csv.reader expects file opened in binary mode
                fbatchManifestErr = open(batchManifestErr, "wb")
                fbatchManifestTemp = open(batchManifestTemp, "wb")
        except IOError:
            logging.fatal("cannot write batch manifest")
            config.errors += 1
            errorExit(config.errors, config.warnings)

        # Create CSV writer objects
        csvErr = csv.writer(fbatchManifestErr, lineterminator='\n')
        csvTemp = csv.writer(fbatchManifestTemp, lineterminator='\n')

        # Write header rows to batch manifests
        csvErr.writerow(self.headerBatchManifest)
        csvTemp.writerow(self.headerBatchManifest)

        # Create list to store all image path directories
        imagePathsIn = []

        # Iterate over all entries in batch manifest

        for row in self.rowsBatchManifest:
            jobID = row[0]
            PPNValue = row[1]

            if PPNValue in config.failedPPNs:
                # If PPN is in list of failed PPNs then add record to error batch

                # Image path for this jobID in input, pruned and error batch
                imagePathIn = os.path.normpath(os.path.join(self.batchDir, jobID))
                imagePathErr = os.path.normpath(os.path.join(config.batchErr, jobID))

                imagePathInAbs = os.path.abspath(imagePathIn)
                imagePathErrAbs = os.path.abspath(imagePathErr)

                if os.path.isdir(imagePathInAbs):

                    # Add path to list
                    imagePathsIn.append(imagePathInAbs)

                    # Create directory in error batch
                    try:
                        os.makedirs(imagePathErrAbs)
                    except (OSError, IOError):
                        logging.error("jobID " + jobID +
                                      ": could not create directory '" +
                                      imagePathErrAbs)
                        config.errors += 1

                    # All files in directory
                    allFiles = glob.glob(imagePathInAbs + "/*")

                    # Copy all files to error batch and do post-copy checksum verification
                    logging.info("Copying files to error batch")

                    for fileIn in allFiles:
                        # File base name
                        fileBaseName = os.path.basename(fileIn)

                        # Path to copied file
                        fileErr = os.path.join(imagePathErrAbs, fileBaseName)

                        # Copy file to batchErr
                        try:
                            shutil.copy2(fileIn, fileErr)
                        except (IOError, OSError):
                            logging.error("jobID " + jobID + ": cannot copy '" +
                                          fileIn + "' to '" + fileErr + "'")
                            config.errors += 1

                        # Verify checksum
                        checksumIn = checksums.generate_file_sha512(fileIn)
                        checksumErr = checksums.generate_file_sha512(fileErr)

                        if checksumIn != checksumErr:
                            logging.fatal("jobID " + jobID + ": checksum of '" +
                                          fileIn + "' does not match '" + fileErr + "'")
                            config.errors += 1
                            errorExit(config.errors, config.warnings)

                # Write row to error batch manifest
                logging.info("Writing batch manifest entry (batchErr)")
                csvErr.writerow(row)

            else:
                # Write row to temp batch manifest
                logging.info("Writing batch manifest entry (batchIn)")
                csvTemp.writerow(row)

        fbatchManifestErr.close()
        fbatchManifestTemp.close()

        if config.errors == 0:

            # Remove directories from input batch
            for imagePath in imagePathsIn:
                logging.info("Removing  directory '" +
                             imagePath + "' from batchIn")
                try:
                    shutil.rmtree(imagePath)
                except OSError:
                    logging.error("cannot remove '" + imagePath + "'")
                    config.errors += 1

            # Rename original batchManifest to '.old' extension
            fileBatchManifestOld = os.path.splitext(self.fileBatchManifest)[0] + ".old"
            batchManifestOld = os.path.join(self.batchDir, fileBatchManifestOld)
            os.rename(self.batchManifest, batchManifestOld)

            # Rename batchManifestTemp to batchManifest
            os.rename(batchManifestTemp, self.batchManifest)

            logging.info("Saved old batch manifest in batchIn as '" +
                         fileBatchManifestOld + "'")

            # Copy batch log to error batch
            batchLogIn = os.path.join(self.batchDir, self.fileBatchLog)
            batchLogErr = os.path.join(config.batchErr, self.fileBatchLog)
            shutil.copy2(batchLogIn, batchLogErr)

        else:
            logging.info("Errors occurred so skipping updating of batch manifests")
            os.remove(fbatchManifestTemp)    

        # Summarise no. of additional warnings / errors during pruning
        logging.info("Pruning resulted in additional " + str(config.errors) +
                     " errors and " + str(config.warnings) + " warnings")
