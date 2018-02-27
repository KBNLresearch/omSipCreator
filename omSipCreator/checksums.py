#! /usr/bin/env python
"""
Checksum reading and generation
"""

import os
import logging
import hashlib
from . import config
from .shared import errorExit


def readChecksums(fileIn):
    """Read checksum file, return contents as nested list
    Also strip away any file paths if they exist (return names only)
    """

    try:
        data = []
        f = open(fileIn, "r", encoding="utf-8")
        for row in f:
            rowSplit = row.split(' ', 1)
            # Second col contains file name. Strip away any path components if they are present
            # Raises IndexError if entry only 1 col (malformed checksum file)!
            fileName = rowSplit[1].strip()
            rowSplit[1] = os.path.basename(fileName)
            data.append(rowSplit)
        f.close()
        return data
    except IOError:
        logging.fatal("cannot read '" + fileIn + "'")
        config.errors += 1
        errorExit(config.errors, config.warnings)


def generate_file_sha512(fileIn):
    """Generate sha512 hash of file
    fileIn is read in chunks to ensure it will work with (very) large files as well
    Adapted from: http://stackoverflow.com/a/1131255/1209004
    """

    blocksize = 2**20
    m = hashlib.sha512()
    with open(fileIn, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()
