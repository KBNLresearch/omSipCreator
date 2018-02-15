#! /usr/bin/env python

"""
Module for writing MODS metadata
"""
import logging
from lxml import etree
from . import config
from .kbapi import sru


def createMODS(PPNGroup):
    """Create MODS metadata based on GGC records in KBMDO
    Dublin Core to MODS mapping follows http://www.loc.gov/standards/mods/dcsimple-mods.html
    General structure: bibliographic md is wrapped in relatedItem / type = host element
    """

    # Dictionary maps carrier types  to MODS resource types
    resourceTypeMap = {
        "cd-rom": "software, multimedia",
        "dvd-rom": "software, multimedia",
        "dvd-video": "moving image",
        "cd-audio": "sound recording"
    }

    PPN = PPNGroup.PPN
    carrierTypes = PPNGroup.carrierTypes

    # Create MODS element
    modsName = etree.QName(config.mods_ns, "mods")
    mods = etree.Element(modsName, nsmap=config.NSMAP)

    # SRU search string (searches on dc:identifier field)
    sruSearchString = '"PPN=' + PPN + '"'
    response = sru.search(sruSearchString, "GGC")

    if not response:
        # Sru.search returns False if no match was found
        noGGCRecords = 0
    else:
        noGGCRecords = response.sru.nr_of_records

    # This should return exactly one record. Return error if this is not the case
    noGGCRecords = response.sru.nr_of_records
    if noGGCRecords != 1:
        logging.error("PPN " + PPN + ": search for PPN=" + PPN + " returned " +
                      str(noGGCRecords) + " catalogue records (expected 1)")
        config.errors += 1
        config.failedPPNs.append(PPN)

    # Select first record
    try:
        record = next(response.records)
        # Extract metadata
        # Title  info can be in either titles element OR in titles element
        # with maintitle attribute
        titlesMain = record.titlesMain
        titles = record.titles
        # Use titlesMain if it exists
        if titlesMain != []:
            titles = titlesMain
        creators = record.creators
        contributors = record.contributors
        publishers = record.publishers
        dates = record.dates
        subjectsBrinkman = record.subjectsBrinkman
        annotations = record.annotations
        identifiersURI = record.identifiersURI
        identifiersISBN = record.identifiersISBN
        recordIdentifiersURI = record.recordIdentifiersURI
        collectionIdentifiers = record.collectionIdentifiers
    except StopIteration:
        # Create empty lists fot all metadata fields in case noGGCRecords = 0
        titles = []
        creators = []
        contributors = []
        publishers = []
        dates = []
        subjectsBrinkman = []
        annotations = []
        identifiersURI = []
        identifiersISBN = []
        recordIdentifiersURI = []
        collectionIdentifiers = []

    # Create MODS entries

    for title in titles:
        modsTitleInfo = etree.SubElement(
            mods, "{%s}titleInfo" % (config.mods_ns))
        modsTitle = etree.SubElement(
            modsTitleInfo, "{%s}title" % (config.mods_ns))
        modsTitle.text = title

    for creator in creators:
        modsName = etree.SubElement(mods, "{%s}name" % (config.mods_ns))
        modsNamePart = etree.SubElement(
            modsName, "{%s}namePart" % (config.mods_ns))
        modsNamePart.text = creator
        modsRole = etree.SubElement(modsName, "{%s}role" % (config.mods_ns))
        modsRoleTerm = etree.SubElement(
            modsRole, "{%s}roleTerm" % (config.mods_ns))
        modsRoleTerm.attrib["type"] = "text"
        modsRoleTerm.text = "creator"

    for contributor in contributors:
        modsName = etree.SubElement(mods, "{%s}name" % (config.mods_ns))
        modsNamePart = etree.SubElement(
            modsName, "{%s}namePart" % (config.mods_ns))
        modsNamePart.text = contributor
        modsRole = etree.SubElement(modsName, "{%s}role" % (config.mods_ns))
        modsRoleTerm = etree.SubElement(
            modsRole, "{%s}roleTerm" % (config.mods_ns))
        modsRoleTerm.attrib["type"] = "text"
        modsRoleTerm.text = "contributor"

    for publisher in publishers:
        modsOriginInfo = etree.SubElement(
            mods, "{%s}originInfo" % (config.mods_ns))
        modsOriginInfo.attrib["displayLabel"] = "publisher"
        modsPublisher = etree.SubElement(
            modsOriginInfo, "{%s}publisher" % (config.mods_ns))
        modsPublisher.text = publisher

    for date in dates:
        # Note that DC date isn't necessarily issue date, and LoC DC to MODS mapping
        # suggests that dateOther be used as default. However KB Metadata model
        # only recognises dateIssued, so we'll use that.
        modsOriginInfo = etree.SubElement(
            mods, "{%s}originInfo" % (config.mods_ns))
        modsDateIssued = etree.SubElement(
            modsOriginInfo, "{%s}dateIssued" % (config.mods_ns))
        modsDateIssued.text = date

    # TODO: perhaps add authority and language attributes
    modsSubject = etree.SubElement(mods, "{%s}subject" % (config.mods_ns))
    for subjectBrinkman in subjectsBrinkman:
        modsTopic = etree.SubElement(
            modsSubject, "{%s}topic" % (config.mods_ns))
        modsTopic.text = subjectBrinkman

    # If all carrierType values within this PPN are identical, map modsTypeOfResource
    # from that value. Otherwise, assign "mixed material"
    if carrierTypes.count(carrierTypes[0]) == len(carrierTypes):
        resourceType = resourceTypeMap[carrierTypes[0]]
    else:
        resourceType = "mixed material"

    modsTypeOfResource = etree.SubElement(
        mods, "{%s}typeOfResource" % (config.mods_ns))
    modsTypeOfResource.text = resourceType

    for annotation in annotations:
        modsNote = etree.SubElement(mods, "{%s}note" % (config.mods_ns))
        modsNote.text = annotation

    # This record establishes the link with the parent publication as it is described
    # in the GGC
    modsRelatedItem = etree.SubElement(
        mods, "{%s}relatedItem" % (config.mods_ns))
    modsRelatedItem.attrib["type"] = "host"

    modsIdentifierPPN = etree.SubElement(
        modsRelatedItem, "{%s}identifier" % (config.mods_ns))
    modsIdentifierPPN.attrib["type"] = "ppn"
    modsIdentifierPPN.text = PPN

    # NOTE: GGC record contain 2 URI- type identifiers:
    # 1. dc:identifier with URI of form: http://resolver.kb.nl/resolve?urn=PPN:236599380 (OpenURL?)
    # 2. dcx:recordIdentifier with URI of form: http://opc4.kb.nl/DB=1/PPN?PPN=236599380
    # URL 1. resolves to URL2, but not sure which one is more persistent?
    # Also a MODS RecordIdentifier field does exist, but it doesn't have a 'type' attribute
    # so we cannot specify it is a URI. For now both are included as 'identifier' elements
    #

    for identifierURI in identifiersURI:
        modsIdentifierURI = etree.SubElement(
            modsRelatedItem, "{%s}identifier" % (config.mods_ns))
        modsIdentifierURI.attrib["type"] = "uri"
        modsIdentifierURI.text = identifierURI

    for identifierISBN in identifiersISBN:
        modsIdentifierISBN = etree.SubElement(
            modsRelatedItem, "{%s}identifier" % (config.mods_ns))
        modsIdentifierISBN.attrib["type"] = "isbn"
        modsIdentifierISBN.text = identifierISBN

    # Add some info on how MODS was generated
    modsRecordInfo = etree.SubElement(
        mods, "{%s}recordInfo" % (config.mods_ns))
    modsRecordOrigin = etree.SubElement(
        modsRecordInfo, "{%s}recordOrigin" % (config.mods_ns))
    originText = "Automatically generated by " + config.scriptName + \
        " v. " + config.version + " from records in KB Catalogue."
    modsRecordOrigin.text = originText

    return mods
