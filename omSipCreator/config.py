#! /usr/bin/env python

"""
Variables that are shared between modules
"""
import sys
import codecs

version = ""
scriptPath = ""
scriptName = ""
mediaInfoExe = ""
mets_ns = ""
mods_ns = ""
premis_ns = ""
ebucore_ns = ""
xlink_ns = ""
xsi_ns = ""
isolyzer_ns = ""
cdInfo_ns = ""
dfxml_ns = ""
metsSchema = ""
modsSchema = ""
premisSchema = ""
ebucoreSchema = ""
NSMAP = {}
failedPPNs = []
errors = 0
warnings = 0
createSIPs = False
pruneBatch = False
skipChecksumFlag = False
batchErr = ""
dirOut = ""
dirsInMetaCarriers = []
carrierTypeAllowedValues = []
# Set encoding of the terminal to UTF-8
if sys.version.startswith("2"):
    out = codecs.getwriter("UTF-8")(sys.stdout)
    err = codecs.getwriter("UTF-8")(sys.stderr)
elif sys.version.startswith("3"):
    out = codecs.getwriter("UTF-8")(sys.stdout.buffer)
    err = codecs.getwriter("UTF-8")(sys.stderr.buffer)
