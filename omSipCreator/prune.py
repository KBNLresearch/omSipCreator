#! /usr/bin/env python
"""
Prune a batch
"""

import sys
import os
import shutil
import glob
import csv
import logging
from . import config
from . import checksums
from .shared import errorExit

def pruneBatch(batchManifest, fileBatchManifest, headerBatchManifest, rowsBatchManifest, out, fileBatchLog):
    """Prune batch"""

    logging.info("Start pruning")

    # Check if batchErr is an existing directory. If yes,
    # prompt user to confirm that it will be overwritten

    if os.path.isdir(config.batchErr):

        out.write("\nThis will overwrite existing directory '" + config.batchErr +
                  "' and remove its contents!\nDo you really want to proceed (Y/N)? > ")
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
    batchManifestErr = os.path.join(config.batchErr, fileBatchManifest)

    # Add temporary (updated) batch manifest to batchIn
    fileBatchManifestTemp = "tmp.csv"
    batchManifestTemp = os.path.join(config.batchIn, fileBatchManifestTemp)

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
    csvErr.writerow(headerBatchManifest)
    csvTemp.writerow(headerBatchManifest)

    # Iterate over all entries in batch manifest

    for row in rowsBatchManifest:
        jobID = row[0]
        PPN = row[1]

        if PPN in config.failedPPNs:
            # If PPN is in list of failed PPNs then add record to error batch

            # Image path for this jobID in input, pruned and error batch
            imagePathIn = os.path.normpath(os.path.join(config.batchIn, jobID))
            imagePathErr = os.path.normpath(os.path.join(config.batchErr, jobID))

            imagePathInAbs = os.path.abspath(imagePathIn)
            imagePathErrAbs = os.path.abspath(imagePathErr)

            if os.path.isdir(imagePathInAbs):

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
                        logging.error("jobID " + jobID + ": checksum of '" +
                                      fileIn + "' does not match '" + fileErr + "'")
                        config.errors += 1

            # Write row to error batch manifest
            logging.info("Writing batch manifest entry (batchErr)")
            csvErr.writerow(row)

            # Remove directory from input batch
            if os.path.isdir(imagePathInAbs):
                logging.info("Removing  directory '" +
                             imagePathInAbs + "' from config.batchIn")
                try:
                    shutil.rmtree(imagePathInAbs)
                except OSError:
                    logging.error("cannot remove '" + imagePathInAbs + "'")
                    config.errors += 1
        else:
            # Write row to temp batch manifest
            logging.info("Writing batch manifest entry (batchIn)")
            csvTemp.writerow(row)

    fbatchManifestErr.close()
    fbatchManifestTemp.close()

    # Rename original batchManifest to '.old' extension
    fileBatchManifestOld = os.path.splitext(fileBatchManifest)[0] + ".old"
    batchManifestOld = os.path.join(config.batchIn, fileBatchManifestOld)
    os.rename(batchManifest, batchManifestOld)

    # Rename batchManifestTemp to batchManifest
    os.rename(batchManifestTemp, batchManifest)

    logging.info("Saved old batch manifest in batchIn as '" +
                 fileBatchManifestOld + "'")

    # Copy batch log to error batch
    batchLogIn = os.path.join(config.batchIn, fileBatchLog)
    batchLogErr = os.path.join(config.batchErr, fileBatchLog)
    shutil.copy2(batchLogIn, batchLogErr)

    # Summarise no. of additional warnings / errors during pruning
    logging.info("Pruning resulted in additional " + str(config.errors) +
                 " errors and " + str(config.warnings) + " warnings")
