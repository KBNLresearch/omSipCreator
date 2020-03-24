from lxml import etree


dfxml_ns = 'http://www.forensicswiki.org/wiki/Category:Digital_Forensics_XML'
dc_ns = 'http://purl.org/dc/elements/1.1/'

NSMAP = {"dfxml": dfxml_ns,
         "dc": dc_ns}

isobusterReport = "/home/johan/kb/testomsipcreator/kb-0b426934-48c2-11ea-bc3f-40b034381df9/0bfc4612-48c3-11ea-b39d-40b034381df9/isobuster-report.xml"

isobusterReportElt = etree.parse(isobusterReport).getroot()
typeElt = isobusterReportElt.xpath('//dfxml:metadata/dc:type', namespaces=NSMAP)
print(typeElt[0].text)
