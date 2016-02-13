#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CitationEntityExtractor is a module, which provides methods for extracting
entities from reference of citation.
"""
from rrslib.db.model import *
from rrslib.xml.xmlconverter import Model2XMLConverter
import StringIO
import entityextractor as ee
import lxml.html as lh
import re
import sys

__modulename__ = "citationentityextractor"
__author__ = "Stanislav Heller"
__email__ = "xlokaj03@stud.fit.vutbr.cz, xhelle03@stud.fit.vutbr.cz"
__date__ = "$1-August-2010 15:58:29$"







#_______________________________________________________________________________


# entityextractor constants
TITLE = ee.TITLE
BOOKTITLE = ee.BOOKTITLE
PUBLISHER = ee.PUBLISHER
PUBLISHED_DATE = ee.PUBLISHED_DATE
AUTHOR = ee.AUTHOR
EDITOR = ee.EDITOR
EVENT = ee.EVENT
ORGANIZATION = ee.ORGANIZATION
LOCATION = ee.LOCATION
ISBN = ee.ISBN
ISSN = ee.ISSN
PAGES = ee.PAGES
VOLUME = ee.VOLUME
TO_APPEAR = ee.TO_APPEAR
TELEPHONE = ee.TELEPHONE
FAX = ee.FAX
PROJECT = ee.PROJECT
URL = ee.URL
# all params together
ALL = ee.ALL

def bin(i):
    """
    In case, that bin() function isnt available, there is need to implement it.
    """
    s = ""
    tmp = i
    while tmp != 0:
        tmp, bit = divmod(tmp, 2)
        s += str(bit)
    return "0b" + s[::-1]




#-------------------------------------------------------------------------------
# entityextractor config file path

#sys.path.append("/media/Data/RRS/rrs_library/src/rrslib/")

try:
    __dictpath = filter(lambda x: x.endswith("/rrslib") or x.endswith("/rrslib/"),
                       sys.path)
    if len(__dictpath) != 0:
        EE_CONFIG_PATH = __dictpath[0].rstrip("/") + "/extractors/entityextractor_method_accuracy.config"
    else:
        __dictpath = filter(lambda x: x.endswith("/rrslib/extractors") or x.endswith("/rrslib/extractors/"),
                       sys.path)
        EE_CONFIG_PATH = __dictpath[0].rstrip("/") + "/entityextractor_method_accuracy.config"
except IndexError:
    EE_CONFIG_PATH = "/".join(__file__.split("/")[:-1]) + "/entityextractor_method_accuracy.config"
    #EE_CONFIG_PATH = "/mnt/minerva1/nlp/projects/rrs_library/rrslib/extractors/entityextractor_method_accuracy.config"
#_______________________________________________________________________________

class CitationEntityExtractorError(Exception):
    pass

#-------------------------------------------------------------------------------
# End of class CitationEntityExtractorError
#-------------------------------------------------------------------------------

class CitationEntityExtractor(object):

    def __init__(self, target=ALL, xmlcompatibility='db08'):
        self.accuracy = {}
        self._load_ee_method_acc()
        self.params = target
        self.entity_extractor = ee.EntityExtractor()
        self.xmlvalid = int(xmlcompatibility.lstrip('db'))


    def _load_ee_method_acc(self):
        s = open(EE_CONFIG_PATH)
        tree = lh.parse(s)
        for method in tree.getroot():
            for m in method[0].iterchildren():
                if float(m.get("accuracy")) in self.accuracy:
                    self.accuracy[float(m.get("accuracy"))].append(ee.METHOD2ENTITY[m.get("name")])
                else:
                    self.accuracy[float(m.get("accuracy"))] = [ee.METHOD2ENTITY[m.get("name")]]
        self.acc_sorted = sorted(self.accuracy.keys(), reverse=True)


    def _publ_credibility(self, publ, init=70):
        def _bracket_alone(text):
            if re.search(" [\(\)\{\}\[\]] ", text):
                return True
            return False

        # default credibility
        cred = init
        if publ.isset('person'): cred += 15
        else: cred -= 5
        #if publ.isset('person_editor'): cred += 10
        if publ.isset('pages'): cred += 10
        else: cred -= 2
        if publ.isset('year'): cred += 5
        else: cred -= 1
        if publ.isset('month'): cred += 5
        else: cred -= 1
        if publ.isset('publisher'): cred += 10
        if publ.isset('title'):
            title = publ.get('title')
            # remove prepositions and words with len(w) < 3
            title = re.sub("(?<= )(?:[fF]or|[iI]n|[oO]f|[oO]n|[aA]t|[Tt]he|"\
                           "[Aa]nd|[aA]|[Ii]s|[Ww]e|[Tt]o)(?= )", "", title)
            title = re.sub("^(?:A|The|In|Is|To) ", "", title)
            title = re.sub("[ ]+", " ", title)
            # split into chunks
            title_sp = title.split(" ")
            _ok = 0
            _bad = 0
            # if there are many chunks (almost-words) with no meaning, reduce
            # credibility value
            _blacklisted = '(?<![a-z])(?:department|faculty|universtiy|society|lab|press|)(?![a-z]+)'
            for chunk in title_sp:
                if re.search(_blacklisted, chunk, re.I):
                    _bad += 1
                elif re.search("[a-z]{3,}", chunk, re.I):
                    _ok += 1
                else:
                    _bad += 1
            # guess accuracy
            negative = float(_bad) / float(len(title_sp))
            cred = float(cred) - negative * 60
            # bonus if all chunks are OK
            if _bad == 0:
                cred += 15
            # if there in title is bracket alone, reduce credibility
            if _bracket_alone(title):
                cred -= 15
        else:
            cred = 0

        # if extracted ratio (extracted/non-extracted text) is too low, reduce
        # credibility as much as params were selected: if ALL, reduce in the whole
        # scale, if only one one param, i.e. TITLE, reduce 1/18 times.
        rest = re.sub("[ \t]+", "", self.rest)
        # compute ratio of "nonextracted"/"all"
        ratio = float(len(rest)) / float(len(self.citation_text))
        # exponential function
        exp = lambda x: (2 ** x - 1)
        # count scale on order of params
        param_bin_str = bin(self.params).lstrip("0b")
        scale = float(param_bin_str.count("1")) / float(18)
        # reduce credibility
        cred -= exp(ratio) * scale * 80
        # if crediblity is out of range, set it to range 0-100
        if cred > 100: cred = 100
        if cred < 0: cred = 0

        # set credibility
        publ.set('credibility', int(cred))
        return publ


    def _publ_type(self, publ):
        # XXX article, book???
        _type = "misc"
        if publ.isset("to_appear"):
            _type = "unpublished"
        elif publ.isset("event"):
            ev = publ.get("event")
            if ev.get("type") != None:
                ev_type = ev.get("type").get("type")
                if ev_type == "conference":
                    _type = "conference"
                else:
                    _type = "inproceedings"
        elif re.search('Ph\.?D thesis', self.citation_text, re.I):
            _type = 'phdthesis'
        elif re.search('Masters? ?thesis', self.citation_text, re.I):
            _type = 'mastersthesis'
        elif re.search(" tech report ", self.citation_text, re.I):
            _type = 'techreport'
        elif publ.isset("title") and re.search(" manual ", publ.get("title"), re.I):
            _type = 'manual'
        elif hasattr(self, 'book'): # XXX journal???
            _type = 'inbook'
        __type = RRSPublication_type(type=_type)
        publ.set('type', __type)
        return publ



    def _whitening(self, text):
        t = re.sub("[^a-zA-Z0-9_\-\:\(\)][\.,][^a-zA-Z0-9_\-\:\(\)]", "", text)
        return re.sub("[ \t\n]+", " ", t)



    #---------------------------------------------------------------------------
    # public methods
    #---------------------------------------------------------------------------

    def set_target(self, target):
        self.params = target


    def get_rest(self):
        return self.rest


    def extract(self, citation):

        if not isinstance(citation, RRSCitation):
            raise CitationEntityExtractorError("citations has to be instance of RRSCitation")
        self.publ = None
        # extracting data
        entities = {}
        if citation.get('reference') != None:
            self.rest = citation.get('reference').get('content')
        else:
            self.rest = ""
        self.citation_text = citation.get('reference').get('content')
        for x in self.acc_sorted:
            for entity_const in self.accuracy[x]:
                if entity_const & self.params:
                    # get extracting method by name
                    extractor_method = getattr(self.entity_extractor, ee.ENTITY2METHOD[entity_const])
                    method_result = extractor_method(self.rest)
                    # if some result, set it to dict
                    if method_result[0] is not None and method_result[0]:
                        result = method_result[0]
                        self.rest = self._whitening(method_result[1])
                        if result is not None:
                            entities[entity_const] = result
        # assign
        self.publ = RRSPublication()
        for entity_key in entities:
            if entity_key == TITLE:
                self.publ.set("title", entities[entity_key])
            elif entity_key == BOOKTITLE:
                self.book = RRSPublication()
                self.book.set("title", entities[entity_key])
            elif entity_key == PUBLISHER:
                _org = RRSOrganization(title=entities[entity_key])
                self.publ.set("publisher", _org)
            elif entity_key == PUBLISHED_DATE:
                d = None
                for date in entities[entity_key]:
                    if date.get('year') < 1940 or date.get('year') > 2100:
                        continue
                    if str(date) > d: d = date
                if d != None:
                    self.publ.set("year", d.get('year'))
                    self.publ.set("month", d.get('month'))
            elif entity_key == ISBN:
                if self.xmlvalid > 8:
                    self.publ.set("isbn", entities[entity_key])
            elif entity_key == AUTHOR:
                # add all found authors
                c = 0
                for author in entities[entity_key]:
                    c += 1
                    _rel = RRSRelationshipPersonPublication(author_rank=c,
                                                            editor=False)
                    #_rel.set_entity(self.publ)
                    _rel.set_entity(author)
                    self.publ.set('person', _rel)
            elif entity_key == EDITOR:
                # set all found editors
                for editor in entities[entity_key]:
                    _rel = RRSRelationshipPersonPublication(editor=True)
                    #_rel.set_entity(self.publ)
                    _rel.set_entity(editor)
                    self.publ.set('person', _rel)
            elif entity_key == TO_APPEAR:
                self.publ.set("to_appear", entities[entity_key])
            elif entity_key == EVENT:
                # for all found events
                for e in entities[entity_key]:
                    # find location in event name if LOCATION is set
                    if LOCATION & self.params:
                        loc, t = self.entity_extractor.find_location(e.get('title'))
                        if loc is not None:
                            for l in loc:
                                e.set('location', l)
                    # assign ISSN to event
                    if ISSN in entities:
                        if self.xmlvalid > 9:
                            e.set('issn', entities[ISSN])
                            del entities[ISSN]
                    self.publ.set("event", e)
            elif entity_key == ORGANIZATION:
                # for all found organiations
                for o in entities[entity_key]:
                    # find location in organization title if LOCATION is set
                    if LOCATION & self.params:
                        loc, t = self.entity_extractor.find_location(o.get('title'))
                        if loc is not None:
                            for l in loc:
                                o.set('location', l)
                    #db09 fix
                    #self.publ.set("organization", o)
                    self.publ.set("publisher", o)
            elif entity_key == PAGES:
                self.publ.set("pages", str(entities[entity_key]))
            elif entity_key == VOLUME:
                self.publ.set("number", entities[entity_key])
            elif entity_key == URL:
                for url in entities[entity_key]:
                    url.set("type", RRSUrl_type(type="publication"))
                    _rel = RRSRelationshipPublicationUrl()
                    #_rel.set_entity(self.publ)
                    _rel.set_entity(url)
                    self.publ.set("url", _rel)
            elif entity_key == PROJECT:
                for p in entities[entity_key]:
                    _rel = RRSRelationshipPublicationProject()
                   # _rel.set_entity(self.publ)
                    _rel.set_entity(p)
                    self.publ.set("project", _rel)

        # location at last
        if LOCATION in entities:
            if self.publ.isset('organization') and self.publ.isset('event'):
                for l in entities[LOCATION]:
                    self.publ.organization.set('location', l)
            elif self.publ.isset('organization'):
                # breaking encapsulation
                for l in entities[LOCATION]:
                    self.publ.organization.set('location', l)
            elif self.publ.isset('event'):
                # breaking encapsulation
                for l in entities[LOCATION]:
                    self.publ.event.set('location', l)

        # set publication crediblity
        self.publ = self._publ_credibility(self.publ)

        # set publication type
        self.publ = self._publ_type(self.publ)
        # set publication into citation object
        if self.xmlvalid >= 9:
            if hasattr(self, 'book'):
                self.book = self._publ_credibility(self.book, init=100)
                citation.set("publication", self.book)
                _rel = RRSRelationshipPublicationCitation()
                _rel.set_entity(self.publ)
                #_rel.set_entity(self.book)
                self.book.set('citation', _rel)
                del self.book
            else:
                citation.set("publication", self.publ)
            #del self.publ
        else:
            citation.set("publication", self.publ)
        
        if citation["reference"] != None:
            citation["reference"].set("referenced_publication", self.publ)

        del self.publ
        entities.clear()

        return citation

#-------------------------------------------------------------------------------
# end of class CitationEntityExtractor
#-------------------------------------------------------------------------------


# main, testing


if __name__ == '__main__':
    txt = "Jack H. Lutz, Resource-bounded measure, Proceedings of the Thirteenth Annual IEEE Conference on Computational Complexity (Buffalo, NY, June 15-18, 1998), IEEE Computer Society Press, 1998, pp. 236-248. "
    txt2 = "Soriano C., Raikundalia G., and Szajman J. A usability study of short message service on middle-aged users. In Proceedings of the 19th conference of the computerhuman interaction special interest group (CHISIG) of Australia on Computer-human interaction. CHISIG of Australia, Narrabundah, Australia, 2005, 1-4."
    txt3 = "Bruce, C., Buckingham, L., Hynd, J., McMahon, C., Roggenkamp, M. and Stoodly, I. Ways of experiencing the act of learning to program: A phenomenographic study of introductory programming students at university. Journal of Information Technology Education, 3:143-160, 2004."
    txt4 = "O'Sullivan, M., Brevik, J., Wolski, R., The Performance of LDPC codes with Large Girth, The Performance of LDPC codes with Large Girth, (to appear) Proc. 43rd Allerton Conference on Communication, Control and Computing, Univ. Illinois, 2005 (PDF). "
    txt5 = "Zapf, D., Brodbeck, F., Frese, M., Peters, H., and Prumper, J. Errors in working with office computers: A first validation of a taxonomy for observed errors in a field setting. International Journal of Human-Computer Interaction"
    txt6 = "B.K.P. Horn, H. Hilden, S. Negahdaripour, Closed-form solution of absolute orientation using unit quaternions, Journal of the Optical Society A 4, 4 (April 1987), 629-642 107"
    txt7 = 'Barhen, J., "Automated Nodal Analysis for CRT Discrimination and Validation", 1993 Joint Services Data Fusion Symposium, Applied Physics Laboratory, Laurel, MD (June 17), Research Manattan Project.'
    txt8 = "Chapter 13: Parallel Linear Algebra Software,  Victor Eijkhout, Julien Langou, and Jack Dongarra, In Frontiers of Parallel Processing for Scientific Computing, M. A. Heroux, P. Raghavan, and H. D. Simon Eds. SIAM Software, Environments and Tools. Society for Industrial and Applied Mathematics, Philadelphia, PA, USA, pages 233-247, 2006. "
    txt9 = "Self Adapting Numerical Software SANS Effort,  George Bosilca, Zizhong Chen, Jack Dongarra, Victor Eijkhout, Graham Fagg, Erika Fuentes, Julien Langou, Piotr Luszczek, Jelena Pjesivac-Grbovic, Keith Seymour, Haihang You, and Satish S. Vadiyar, The University of Tennessee, Computer Science Department Tech Report UT-CS-05-554, June 2005, IBM Journal of Reseach and Development, pp 223-238, Volume 50, Number 2/3, 2006"
    txt10 = "Chisholm, Malcolm. The Black Box Problem. Business Rules Journal, Vol. 3, No. 3, (March 2002). http://www.BRCommunity.com/a2002/b100.html."
    txt11 = "W. Yu, H. Hoogeveen and J.K. Lenstra. Minimizing makespan in a two-machine flowshop with delays and unit-time operations is NP-hard. Journal of Scheduling, 7(5), 333-348, 2004."
    txt12 = "19. W. C. Wang and Z. P. Xin, On small mean free path limit of Broadwell model with discontinuous initail data, the centered rarefaction wave case, J. Differential Equations 150, No. 2 (1998), 438 461."
    txt13 = "[1] S. Acharya, P. B. Gibbons, and V. Poosala. Congressional samples for approximate answering of group-by queries. In Proc. ACM SIGMOD International Conf. on Management of Data, New York, USA, pages 487498, May 2000."
    txt14 = "Z. Lin, M. Broucke, and B. Francis, &quot;Local control strategies for groups of mobile autonomous agents,&quot; IEEE Transactions on Automatic Control, vol. 49, no. 4, pp. 622629, April 2004."
    txt15 = "Ayako Ikeno, Bryan Pellom, Dan Cer, Ashley Thornton, Jason Brenier, Dan Jurafsky, Wayne Ward, William Byrne, &quot;Issues in Recognition of Spanish-Accented Spontaneous English&quot; , in ISCA &amp; IEEE ISCA &amp; IEEE Workshop on Spontaneous Speech Processing and Recognition, Tokyo, Japan, April, 2003, ISBN 85-359-0277-5"
    txt16 = "KLAPKA, J. Influence of Wall Losses on Energy Flow Center Velocity of Pulses in Waveguides. IEEE Transactions on Microwave Theory and Techniques, 1970, vol. MTT-18, no. 10, p. 689-696. ISSN: 0018-9480."
    txt17 = " BABINEC, F. Fuzzy knowledge transfer in process engineering. In EUFIT94-Intelligent Techniques and Soft Computing. Aachen, Germany: Verlag der Augustinus Buchhandlung, Pontstrasse 66, 1900. p. 1278-1286. ISBN: 3-86073-28."

    ame = CitationEntityExtractor(ALL, xmlcompatibility='db09')
    output = StringIO.StringIO()
    converter = Model2XMLConverter(stream=output)
    _l = []
    #for t in(txt15,):
    for t in (txt, txt2, txt3, txt4, txt5, txt6, txt7, txt8, txt9, txt10, txt11, txt12, txt13, txt14, txt15, txt16, txt17):
        r = RRSReference(content=t)
        c = RRSCitation(content = "a")
	c['reference'] = r
      
        e = ame.extract(c)
        #print id(c), id(e)
        #print e
	_l.append(e)
    #converter.convert(_l)
    #print output.getvalue()

