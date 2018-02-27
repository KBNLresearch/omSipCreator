#! /usr/bin/env python
"""Wrapper module for reading and parsing cd-info output"""

import io
from lxml import etree
from . import shared
from . import config


def parseCDInfoLog(fileCDInfo):
    """Determine carrier type and number of sessions on carrier"""

    # Create cd-info element
    cdInfoName = etree.QName(config.cdInfo_ns, "cd-info")
    cdInfoElt = etree.Element(
        cdInfoName, nsmap=config.NSMAP)

    # Add trackList and analysisReport elements
    trackListElt = etree.SubElement(cdInfoElt,
                                    "{%s}trackList" % (config.cdInfo_ns))
    analysisReportElt = etree.SubElement(cdInfoElt,
                                         "{%s}analysisReport" % (config.cdInfo_ns))

    # Open cd-info log file and read to list
    outAsList = []

    with io.open(fileCDInfo, "r", encoding="utf-8") as fCdInfoLogFile:
        for line in fCdInfoLogFile:
            line = line.strip()
            outAsList.append(line)
    fCdInfoLogFile.close()

    # Set up list and empty string for storing analysis report
    analysisReport = []
    analysisReportString = ''

    # Initialise variable that reports LSN of data track
    dataTrackLSNStart = 0

    # Locate track list and analysis report in cd-info output
    startIndexTrackList = shared.index_startswith_substring(outAsList, "CD-ROM Track List")
    startIndexAnalysisReport = shared.index_startswith_substring(outAsList, "CD Analysis Report")

    # Parse track list and store interesting bits in dictionary
    for i in range(startIndexTrackList + 2, startIndexAnalysisReport - 1, 1):
        thisTrack = outAsList[i]
        if not thisTrack.startswith("++"):  # This gets rid of warning messages, do we want that?
            thisTrack = thisTrack.split(": ")
            trackNumber = int(thisTrack[0].strip())
            trackDetails = thisTrack[1].split()
            trackMSFStart = trackDetails[0]  # Minute:Second:Frame
            trackLSNStart = trackDetails[1]  # Logical Sector Number
            trackType = trackDetails[2]  # Track type: audio / data
            trackGreen = trackDetails[3]  # Don't  know what this means
            trackCopy = trackDetails[4]  # Don't  know what this means
            if trackType == 'audio':
                trackChannels = trackDetails[5]
                trackPreemphasis = trackDetails[6]

            if trackType == 'data':
                dataTrackLSNStart = int(trackLSNStart)

            # Append properties to trackList
            trackElt = etree.SubElement(trackListElt,
                                        "{%s}track" % (config.cdInfo_ns))
            trackNumberElt = etree.SubElement(trackElt,
                                              "{%s}trackNumber" % (config.cdInfo_ns))
            trackNumberElt.text = str(trackNumber)
            MSFElt = etree.SubElement(trackElt,
                                      "{%s}MSF" % (config.cdInfo_ns))
            MSFElt.text = trackMSFStart
            LSNElt = etree.SubElement(trackElt,
                                      "{%s}LSN" % (config.cdInfo_ns))
            LSNElt.text = str(trackLSNStart)
            TypeElt = etree.SubElement(trackElt,
                                       "{%s}Type" % (config.cdInfo_ns))
            TypeElt.text = trackType
            if trackType != 'leadout':
                GreenElt = etree.SubElement(trackElt,
                                            "{%s}Green" % (config.cdInfo_ns))
                GreenElt.text = trackGreen
                CopyElt = etree.SubElement(trackElt,
                                           "{%s}Copy" % (config.cdInfo_ns))
                CopyElt.text = trackCopy
            if trackType == 'audio':
                ChannelsElt = etree.SubElement(trackElt,
                                               "{%s}Channels" % (config.cdInfo_ns))
                ChannelsElt.text = trackChannels
                PreemphasisElt = etree.SubElement(trackElt,
                                                  "{%s}Preemphasis" % (config.cdInfo_ns))
                PreemphasisElt.text = trackPreemphasis

    # Parse analysis report
    for i in range(startIndexAnalysisReport + 1, len(outAsList), 1):
        thisLine = outAsList[i]
        analysisReport.append(thisLine)
        analysisReportString = analysisReportString + thisLine + "\n"

    # Flags for CD/Extra / multisession / mixed-mode
    # Note that single-session mixed mode CDs are erroneously reported as
    # multisession by libcdio. See: http://savannah.gnu.org/bugs/?49090#comment1
    cdExtra = shared.index_startswith_substring(analysisReport, "CD-Plus/Extra") != -1
    multiSession = shared.index_startswith_substring(analysisReport, "session #") != -1
    mixedMode = shared.index_startswith_substring(analysisReport, "mixed mode CD") != -1

    # Add individual parsed values from analysis report to separate subelements
    cdExtraElt = etree.SubElement(analysisReportElt,
                                  "{%s}cdExtra" % (config.cdInfo_ns))
    cdExtraElt.text = str(cdExtra)
    multiSessionElt = etree.SubElement(analysisReportElt,
                                       "{%s}multiSession" % (config.cdInfo_ns))
    multiSessionElt.text = str(multiSession)
    mixedModeElt = etree.SubElement(analysisReportElt,
                                    "{%s}mixedMode" % (config.cdInfo_ns))
    mixedModeElt.text = str(mixedMode)

    # Add unformatted analysis report to analysisReportFullElt element
    analysisReportFullElt = etree.SubElement(analysisReportElt,
                                             "{%s}fullReport" % (config.cdInfo_ns))
    analysisReportFullElt.text = analysisReportString

    return cdInfoElt, dataTrackLSNStart
