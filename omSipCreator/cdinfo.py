#! /usr/bin/env python
"""Wrapper module for reading and parsing cd-info output"""

import io
from . import shared

def parseCDInfoLog(fileCDInfo):
    """Determine carrier type and number of sessions on carrier"""

    # Open cd-info log file and read to list
    outAsList = []    

    with io.open(fileCDInfo, "r", encoding="utf-8") as fCdInfoLogFile:
        for line in fCdInfoLogFile:
            line = line.strip()
            outAsList.append(line)
    fCdInfoLogFile.close()

    # Set up dictionary and list for storing track list and analysis report
    trackList = []
    analysisReport = []

    # Locate track list and analysis report in cd-info output
    startIndexTrackList = shared.index_startswith_substring(outAsList, "CD-ROM Track List")
    startIndexAnalysisReport = shared.index_startswith_substring(outAsList, "CD Analysis Report")

    # Parse track list and store interesting bits in dictionary
    for i in range(startIndexTrackList + 2, startIndexAnalysisReport - 1, 1):
        thisTrack = outAsList[i]
        if not thisTrack.startswith("++"):
            thisTrack = thisTrack.split(": ")
            trackNumber = int(thisTrack[0].strip())
            trackDetails = thisTrack[1].split()
            trackMSFStart = trackDetails[0]  # Minute:Second:Frame
            trackLSNStart = trackDetails[1]  # Logical Sector Number
            trackType = trackDetails[2]
            trackProperties = {}
            trackProperties['trackNumber'] = trackNumber
            trackProperties['trackMSFStart'] = trackMSFStart
            trackProperties['trackLSNStart'] = trackLSNStart
            trackProperties['trackType'] = trackType
            trackList.append(trackProperties)

    # Flags for presence of audio / data tracks
    containsAudio = False
    containsData = False
    dataTrackLSNStart = '0'

    for track in trackList:
        if track['trackType'] == 'audio':
            containsAudio = True
        if track['trackType'] == 'data':
            containsData = True
            dataTrackLSNStart = track['trackLSNStart']

    # Parse analysis report
    for i in range(startIndexAnalysisReport + 1, len(outAsList), 1):
        thisLine = outAsList[i]
        if not thisLine.startswith("++"):
            analysisReport.append(thisLine)

    # Flags for CD/Extra / multisession / mixed-mode
    # Note that single-session mixed mode CDs are erroneously reported as
    # multisession by libcdio. See: http://savannah.gnu.org/bugs/?49090#comment1

    cdExtra = shared.index_startswith_substring(analysisReport, "CD-Plus/Extra") != -1
    multiSession = shared.index_startswith_substring(analysisReport, "session #") != -1
    mixedMode = shared.index_startswith_substring(analysisReport, "mixed mode CD") != -1

    # Main results to dictionary
    dictOut = {}
    dictOut["cdExtra"] = cdExtra
    dictOut["multiSession"] = multiSession
    dictOut["mixedMode"] = mixedMode
    dictOut["containsAudio"] = containsAudio
    dictOut["containsData"] = containsData
    dictOut["dataTrackLSNStart"] = dataTrackLSNStart
    dictOut["trackList"] = trackList

    return dictOut
