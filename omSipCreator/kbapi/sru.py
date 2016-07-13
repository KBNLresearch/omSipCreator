import sys
import requests
import urllib
from lxml import etree

SRU_BASEURL = 'http://jsru.kb.nl/sru/sru'
SRU_BASEURL += '?version=1.2&maximumRecords=%i'
SRU_BASEURL += '&operation=searchRetrieve'
SRU_BASEURL += '&startRecord=%i'
SRU_BASEURL += '&recordSchema=%s'
SRU_BASEURL += '&x-collection=%s&query=%s'

SETS = {'ANP': {'collection': 'ANP',
                'description_en': 'Radio Bulletins ANP Press Agency',
                'description_nl': 'ANP Radiobulletins Digitaal',
                'metadataPrefix': 'didl',
                'recordschema': 'dcx',
                'setname': 'anp',
                'time_period': [1937, 1989]},
        'DPO': {'collection': 'DPO_boekdeel',
                'description_en': 'Early Dutch Books Online',
                'description_nl': 'Early Dutch Books Online',
                'metadataPrefix': 'didl',
                'recordschema': 'ddd',
                'setname': 'DPO',
                'time_period': [1781, 1800]},
        'BYVANCK': {'description_en': 'Medieval Illuminated Manuscripts',
                    'description_nl': 'Middeleeuwse Verluchte Handschriften',
                    'metadataPrefix': 'dcx',
                    'setname': 'BYVANCK',
                    'time_period': [500, 1500]},
        'SGD': {'description_en': 'States General Digital',
                'description_nl': 'Staten-Generaal Digitaal',
                'metadataPrefix': 'dcx',
                'setname': 'sgd:register',
                'time_period': [1962, 1994]},
        'GGC': {'collection': 'GGC',
                'description_en': 'General Catalogue KB',
                'description_nl': 'Algemene Catalogus KB',
                'metadataPrefix': 'dcx',
                'recordschema': 'dcx',
                'setname': 'ggc',
                'time_period': [1937, 2016]}} # No idea what to use here?

# Name spaces in GGC records 

srw_ns = 'http://www.loc.gov/zing/srw/'
tel_ns = 'http://krait.kb.nl/coop/tel/handbook/telterms.html'
xsi_ns = 'http://www.w3.org/2001/XMLSchema-instance'
dc_ns = 'http://purl.org/dc/elements/1.1/'
dcterms_ns = 'http://purl.org/dc/terms/'
dcx_ns = 'http://krait.kb.nl/coop/tel/handbook/telterms.html'
    
NSMAPGGC =  {"srw" : srw_ns,
         "tel" : tel_ns,
         "xsi" : xsi_ns,
         "dc" :  dc_ns,
         "dcterms" : dcterms_ns,
         "dcx" : dcx_ns}

class response():
    def __init__(self, record_data, sru):
        self.record_data = record_data
        self.sru = sru
    
    @property
    def records(self):
        if self.sru.nr_of_records == 0:
            record_data = "<xml></xml>"
        else:
            ns = {'zs': 'http://www.loc.gov/zing/srw/'}
            record_data = self.record_data.xpath("zs:records/zs:record",
                                                 namespaces=ns)[0]
        return(record(record_data, self.sru))

    # TODO: distinguish by xsi:type 
    @property
    def identifiers(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('identifier')]
    """
    @property
    def uris(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('identifier')]
    """
    @property
    def uris(self):
        myURIS = []
        for r in self.record_data.iter():
            if r.tag.endswith('identifier'):
                attributes = r.attrib
                try:
                    if attributes['{http://www.w3.org/2001/XMLSchema-instance}tupe'] == 'dcterms:URI':
                        myURIS.append(r.text)
                except KeyError:
                    pass
        return(myURIS)
   
    @property
    def types(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('type')]
    
    @property
    def languages(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('language')]
   
    @property
    def dates(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('date')]

    @property
    def extents(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('extent')]

    @property
    def creators(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('creator')]

    @property
    def contributors(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('contributor')]

    # TODO: distinguish by xsi:type and xml:lang
    @property
    def subjects(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('subject')]

    @property
    def abstracts(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('abstract')]

    @property
    def titles(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('title')]

    @property
    def publishers(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('publisher')]

    # Following properties occur in GGC

    @property
    def annotations(self):
        return [r.text for r in self.record_data.iter() if
                r.tag.endswith('annotation')]


class record():
    def __init__(self, record_data, sru):
        self.record_data = record_data
        self.sru = sru

    def __iter__(self):
        return self

    def next(self):
        if self.sru.nr_of_records == 0:
            raise StopIteration
        if self.sru.startrecord < self.sru.nr_of_records + 1:
            record_data = self.sru.run_query()
            self.sru.startrecord += 1
            return response(record_data, self.sru)
        else:
            raise StopIteration

class sru():
    DEBUG = False

    collection = False
    maximumrecords = 50
    nr_of_records = 0
    query = ""
    recordschema = False
    sru_collections = SETS
    startrecord = 0

    def search(self, query, collection=False,
               startrecord=1, maximumrecords=1, recordschema=False):

        self.maximumrecords = maximumrecords
        self.query = urllib.quote_plus(query)
        self.startrecord = startrecord

        if collection not in self.sru_collections:
                raise Exception('Unknown collection')

        self.collection = self.sru_collections[collection]['collection']

        if not self.collection:
            raise Exception('Error, no collection specified')

        if not recordschema:
                self.recordschema = self.sru_collections[collection]['recordschema']
        else:
                self.recordschema = recordschema

        record_data = self.run_query()

        nr_of_records = [i.text for i in record_data.iter() if
                         i.tag.endswith('numberOfRecords')][0]

        self.nr_of_records = int(nr_of_records)

        if nr_of_records > 0:
            return response(record_data, self)

        return False

    def run_query(self):
        url = SRU_BASEURL % (self.maximumrecords, self.startrecord,
                             self.recordschema, self.collection, self.query)
        if self.DEBUG:
                sys.stdout.write(url)

        r = requests.get(url)

        if not r.status_code == 200:
            raise Exception('Error while getting data from %s' % url)

        record_data = etree.fromstring(r.content)


        return record_data
