#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module webmetaextractor contains various web extractors which usually acts as
components for web extractors in RRS. There are components for extracting data
from pages containing publication lists, homepages and also web page classifier.

Some day this module will contain also WebMetaExtractor, the highest-level extractor
which on the basis of page classification and usage of focused extractors will
extract data from every (usefull of course) webpage.

THIS MODULE NEEDS TO BE IMPROVED AND TESTED!
"""

__modulename__ = "webmetaextractor"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$2-September-2010 12:19:57$"

import re
from difflib import SequenceMatcher

from lxml.etree import _ElementTree
from lxml.html import tostring
from lxml.html.clean import Cleaner


from copy import deepcopy

from rrslib.extractors.citationentityextractor import CitationEntityExtractor, ALL
from rrslib.db.model import *

from rrslib.extractors.entityextractor import EntityExtractor
from rrslib.extractors.bibtexparser import BibTeXParser

from rrslib.web.crawler import Crawler, FileDownloader
from rrslib.web.mime import MIMEhandler
from rrslib.web.sequencewrapper import HTMLSequenceWrapper
from rrslib.web.htmltools import HTMLDocument, SimpleHTMLCleaner

# import psyco to improve speed
try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")

#_______________________________________________________________________________


class PublicationListExtractor(object):
    """
    PublPageMetaExtractor handles harvests metadata from web pages containing
    references (publication list). For parsing sequences in HTML dom we use
    extractors.sequencewrapper.HTMLSequenceWrapper. For parsing citations
    (records in data regions, which were found by sequencewrapper) we use
    extractors.citationentityextractor.CitationEntityExtractor.

    To improve accuracy of this system, we check headers wheather they contain some
    keyword, which could help us to determine the correct type of publication.

    From headers we also harvest keywords.
    """

    entitydefstr = {'216': 'O', '217': 'U', '214': 'O', '197': 'A',
    '198': 'E', '210': 'O', '211': 'O', '195': 'A', '194': 'A',
    '196': 'A', '193': 'A', '192': 'A', '251': 'u', '252': 'u', '238': 'i',
    '239': 'i', '235': 'e', '234': 'e', '212': 'O', '236': 'e', '237': 'i',
    '230': 'e', '231': 'c', '232': 'e', '213': 'O', '224': 'a', '249': 'u',
    '253': 'y', '248': 'o', '243': 'o', '255': 'y', '250': 'u',
    '233': 'e', '201': 'E', '200': 'E', '203': 'E', '202': 'E', '205': 'I',
    '204': 'I', '207': 'I', '206': 'I', '242': 'o', '220': 'U',
    '245': 'o', '244': 'o', '246': 'o', '241': 'n', '218': 'U', '229': 'a',
    '228': 'a', '227': 'a', '226': 'a', '225': 'a', '219': 'U', '221': 'Y',
    # these are added
    '248': 'r', '185': 's', '174': 'Z', '232': 'c', '200': 'C', '169': 'S', '190': 'z',
    '199': 'C', 'amp': '&', 'nbsp': ' ', 'quot': '\"'
    }

    def __init__(self, xmlcompatibility='db09'):
        self.seqwrapper = HTMLSequenceWrapper(childcoef=7.0, headercoef=3.0, mintextlen=30)
        self.citaextractor = CitationEntityExtractor(ALL, xmlcompatibility=xmlcompatibility)
        self.ee = EntityExtractor()
        self.mime = MIMEhandler()
        self.crawler = Crawler()
        self.bibtex = BibTeXParser()
        self.xmlcompatibility = xmlcompatibility
        self._xmlvalid = int(xmlcompatibility.lstrip('db'))
        self._publ_list = []


    def _set_new_topic(self, publ, kw):
        """
        This method adds new topic to publication.
        """
        if not re.search("[a-z]{4,}", kw):
            return publ
        if re.search("publi|paper", kw, re.I):
            return publ
        t = RRSTopic(title=kw)
        publ.set('topic', t)
        return publ


    def _set_publ_type(self, header, publ):
        def _floor(i):
            if i > 100: i=100
            return i

        if header is None: return publ
        # try to set publication type from header
        for _type in RRSPublication.publication_types:
            if re.search(_type, header, re.I):
                if publ.get('type') == _type:
                    publ.set('credibility', _floor(publ.get('credibility')))
                else:
                    publ.set('type', _type)
                return publ
        if re.search("dissertation", header, re.I):
            publ.set('type', 'phdthesis')
            return publ
        if re.search('technical report', header, re.I):
            publ.set('type', 'techreport')
            return publ
        # make keyword from header
        return self._set_new_topic(publ, header)


    def translate_html_entities(self, text):
        ents = re.findall(r'&(#?)(x?)(\w+);', text)
        for ent in set(ents):
            try:
                text = re.sub('&(#?)'+re.escape(ent[2])+";", self.entitydefstr[ent[2]], text)
            except: pass
        return text


    def compare_chunks_to_extracted(self, chunks, publ):
        if not publ.get('title'): return publ
        title = self.translate_html_entities(publ.get('title'))
        authors = publ.get('person_author')
        author_names = [a.get('name')[0].get('full_name') for a in authors]
        for ch in chunks:
            l = ch.get_link()
            # get chunk text
            ch = self.translate_html_entities(ch.get_text())
            # add url if available
            if l is not None and not l.startswith("javascript") and l != "#":
                u = RRSUrl(type='publication', title=ch, link=l)
                publ.set('url', u)

            # repair title if needed
            if ch in title or ch == title:
                if float(len(ch))/float(len(title)) > 0.4:
                    publ.set('title', ch)
            # repair names if needed
            for a in author_names:
                if a in ch:
                    authors_extracted = self.ee.find_authors(ch)
                    publ.person_author = authors_extracted[0]
                break
        return publ


    def _fill_citation(self, publ):
        c = RRSCitation()
        c.set('content', self.cita_text)
        if publ.get('event'):
            c.set('event', publ.get('event')[0].get('title'))
        return c


    def _handle_bibtex_pages(self):
        urls = {}
        for i, p in enumerate(self._publ_list):
            pub_u = p.get('url')
            for u in pub_u:
                urls[u.get('link')] = i

        #if link is web page, not pdf
        urls_to_download = []
        content_types = self.mime.start(urls.keys())
        for k in urls.keys():
            if content_types[k] in ('text/html', 'application/xhtml+xml',
                                    'application/x-httpd-php', 'text/javascript'):
                urls_to_download.append(k)
        # download page a try it for bibtex
        pages = self.crawler.start(urls_to_download)

        for u in urls_to_download:
            bibtex = self.bibtex.parse(pages[u])
            # if bibtex on page, set publication
            if bibtex is not None:
                self._publ_list[urls[u]] = bibtex


    def _empty(self):
        for x in range(len(self._publ_list)):
            self._publ_list.pop()
        self.cita_text = None


    def _handle_document(self, doc):
        self._empty()
        # for all regions which were found
        for reg in doc.get_regions():
            # get their header
            header = reg.get_name()
            # for all records in region
            for rec in reg._manual_process_page():
                # create empty citation object
                c = RRSCitation()
                # harvest citation record text (probably citation we hope)
                self.cita_text = self.translate_html_entities(rec.get_text())
                # set the content of record to citation object
                c.set('content', self.cita_text)
                # fill object it wih extracted data
                c = self.citaextractor.extract(c)

                # get extracted publication
                publ = c.get('publication_cited')
                # if sequencewrapper extracted come text chunks, it helps us a lot,
                # beacause we can compare extracted data to chunks and if not matched
                # we can fix it
                publ = self.compare_chunks_to_extracted(rec.get_chunks(), publ)
                # insert citation into publication
                # !!! we are extracting publications, not citations. Because we dont
                # want tree like this: citation->publication but this:
                # publication->citation
                publ.set('citation', self._fill_citation(publ))
                # try to find publication type in header of data region
                publ = self._set_publ_type(header, publ)
                # add to publication list
                self._publ_list.append(publ)
        #self._handle_bibtex_pages()
        return self._publ_list

    #---------------------------------------------------------------------------
    # public methods
    #---------------------------------------------------------------------------
    def extract_data(self, tree, url):
        """
        Main method for extracting publication metadata from page.
        """
        # wrap html document
        document = self.seqwrapper.wrap_h(tree, url)
        # handle it and return the result
        return self._handle_document(document)

#-------------------------------------------------------------------------------
# end of class PublicationListExtractor
#-------------------------------------------------------------------------------

class _RRSPropertyGeneralizer(object):
    _known_contexts = ['publication', 'event', 'person', 'organization']
    term2lemma = {
        'editors name': 0,
        'editors': 0,
        'editor name': 0,
        'edited by': 0,

        'timestamp': 1,
        'datestamp': 1,
        'deposited on': 1,
        'deposited': 1,
        'date published': 1,
        'published': 1,

        'subject': 2,
        'subjects': 2,

        'pagerange': 3,
        'page': 3,

        'starting page': 4,
        'start page': 4,
        'beginning': 4,

        'ending page': 5,
        'end page': 5,

        'creator': 6,
        'creators name': 6,
        'creator name': 6,
        'created by': 6,
        'contributor': 6,
        'contributed': 6,
        'by': 6,

        #'description': 7,

        'keyword': 8,
        'key words': 8,

        'item type': 10,
        'publication type': 10,
        'paper type': 10,
        'category': 10,

        'document url': 14,

        'similar publications': 20,
        'related publications': 20,
        'related': 20,
        'related work': 20,

        'comments on this publication': 21,
        'comment': 21,
        'comments': 21,

        'references': 22,
        'references in article': 22,
        'references in publication': 22,
        'references in paper': 22,

        'there are reviews': 23,
        'selected reviews': 23,
        'publication review': 23,
        'publication reviews': 23,
    }

    lemmas = ['editor', 'date', 'topic', 'pages', 'start page', #0-4
              'end page', 'author', 'abstract', 'keywords', 'title', #5-9
              'type', 'isbn', 'publisher', 'citation', 'url', # 10-14
              'volume', 'number', 'acronym', 'issn', 'note', #15-19
              'related', 'comments', 'references', 'reviews'] #20-23


    def generalize(self, term):
        # preprocessing
        term = term.lower()
        term = re.sub("[\"\'0-9]+", "", term)
        term = re.sub("[_:\-\.\,]+", " ", term)
        term =  SimpleHTMLCleaner.clean(term)

        # if it is lemma, its OK
        if self.is_lemma(term):
            return term
        # if it isnt lemma, do lookup
        try:
            index = self.term2lemma[term]
            return self.lemmas[index]
        except KeyError:
            return None


    def is_lemma(self, lemma):
        return lemma in self.lemmas

#-------------------------------------------------------------------------------
# End of class _RRSPropertyGeneralizer
#-------------------------------------------------------------------------------

class ListedDict(dict):
    def __setitem__(self, key, value):
        if key in self:
            if isinstance(value, (list, tuple)):
                self[key].extend(list(value))
            else:
                self[key].append(value)
        else:
            dict.__setitem__(self, key, [value])

    def _longest_val(self):
        v = [""]
        k = [] # k = None
        for x in self:
            if len( self[x] ) > len(v[0]):
                v = [self[x]] # v= self[x]
                k = [x]       # k = x
            elif len( self[x] ) == len(v[0]):
                v.append(self[x])
                k.append(x)
        return (k, v)

    def longest_value(self):
        return self._longest_val()[1]

    def key_of_longest_value(self):
        return self._longest_val()[0]

    def item_by_longest_value(self):
        return self._longest_val()



class PublicationPageExtractor(object):
    """
    This class wraps all methods for recognition publication and it's description
    on the web page.

    The result of page-processing is ORM object rrslib.db.model.RRSPublication
    with extracted data.
    """
    # what could an abstract start with
    _abstract_startswith = ('We present', 'This paper', 'This publica',
                            'In this p', 'The paper', 'This book')
    _abstract_blacklist = ('CiteU', 'Was ', 'I ha', 'I pre', 'I was', 'CiteS',
                           'Microso')
    # tags representing lists in HTML
    _list_tags = ('ol', 'ul', 'dl')
    # tags representing list items in HTML
    _list_item_tags = ('li', 'dd', 'dt')
    # ommitted tags - they are useless for this reason
    _omitted_tags = ('form', 'option', 'link', 'style', 'meta', 'head', 'script')
    # acceptable mime types for documents (publications)
    _accepted_mime = ('application/pdf', 'application/rtf', 'application/postscript', 'application/msword')

    def __init__(self, headercoef=2.5):
        """
        Constructor.
        @param headercoef: lower border of elemet's visibility to be handled as header
        """
        self.generalizer = _RRSPropertyGeneralizer()
        self.ee = EntityExtractor()
        self.headercoef = headercoef
        self.bibtexparser = BibTeXParser()
        self.crawler = Crawler()
        self.mime_handler = MIMEhandler()
        self.crawler.set_handler(FileDownloader)


    def _get_visibility2elem_map(self, etree):
        htmlroot = etree.getroot()
        visibility2elem_map = {}
        for elem in htmlroot.iterdescendants():
            # no need to get those
            if elem.tag in self._omitted_tags: continue
            assert hasattr(elem, 'style')
            v = elem.style.get_visibility()
            if v in visibility2elem_map:
                visibility2elem_map[v].append(elem)
            else:
                visibility2elem_map[v] = [elem]
        return visibility2elem_map


    def _classify_publ_title(self, title, init=70):
        def _bracket_alone(text):
            if text is not None and re.search(" [\(\)\{\}\[\]] ", text):
                return True
            return False
        # default credibility
        cred = init
        # remove prepositions and words with len(w) < 3
        title = re.sub("(?<= )(?:[fF]or|[iI]n|[oO]f|[oO]n|[aA]t|[Tt]he|"\
                       "[Aa]nd|[aA]|[Ii]s|[Ww]e|[Tt]o)(?= )", "", title)
        title = re.sub("^(?:A|The|In|Is|To) ", "", title)
        title = re.sub("[ ]+", " ", title)
        # split into chunks
        title_sp = title.split(" ")
        _bad = 0
        # if there are many chunks (almost-words) with no meaning, reduce
        # credibility value
        _blacklisted = '(?<![a-z])(?:department|faculty|universtiy|society|lab|press|)(?![a-z]+)'
        for chunk in title_sp:
            if re.search(_blacklisted, chunk, re.I):
                _bad += 1
            elif re.search("[a-z]{3,}", chunk, re.I):
                pass
            else:
                _bad += 1
        # guess accuracy
        negative = float(_bad) / float(len(title_sp))
        cred = float(cred) - negative * 65
        # bonus if all chunks are OK
        if _bad == 0:
            cred += 20
        # if there in title is bracket alone, reduce credibility
        if _bracket_alone(title):
            cred -= 15
        # floor
        if cred > 100: cred = 100
        if cred < 0: cred = 0
        return cred


    def _most_alike_term(self, term, target, threshold=0.3):
        assert len(target) > 0
        assert term is not None
        l = ListedDict()
        for t in target:
            s = SequenceMatcher(None, term, t)
            l[float(s.ratio())] = t
        m = max(l)
        if m < float(threshold):
            return None
        return l[m][0]

    def _add_property(self, property, values):
        # Add the property and its value into publication
        # maybe it is not a property, but an entity
        firstval = values[0]
        if firstval is None: return
        # First try to get attributes of the publication
        if property in ('abstract', 'isbn', 'issn', 'volume',
                        'number', 'acronym', 'issn', 'note'):
            _type = self._publ.__types__[property]
            if _type is basestring:
                _type = unicode
            self._publ[property] = (_type)(firstval)
        elif property == 'title':
            self._publ[property] = firstval
            # the origin is from meta-tag, so we are pretty sure about this information
            self._publ['credibility'] = 95
        elif property == 'publisher':
            self._publ['publisher'] = RRSOrganization(title=firstval)
        elif property == 'date':
            r = self.ee.find_published_date(firstval)
            if not r[0]: return
            rrsdate = r[0][0]
            for attr in ('year', 'month'):
                if rrsdate.get(attr) is not None:
                    self._publ[attr] = rrsdate.get(attr)
        elif property == 'type':
            # choose better heuristics
            publtype = self._most_alike_term(firstval, publication_types, 0.4)
            if publtype is not None:
                self._publ['type'] = RRSPublication_type(type=publtype)
        elif property == 'pages':
            if re.search("[0-9]+\-{1,2}[0-9]+", firstval):
                self._publ['pages'] = firstval
        elif property == 'start page':
            if not re.search("^[0-9]+$", firstval): return
            if 'end page' in self._storage and not 'pages' in self._publ:
                self._publ['pages'] = "%s-%s" % (firstval, self._storage['end page'][0])
            else:
                self._storage[property] = [firstval]
        elif property == 'end page':
            if not re.search("^[0-9]+$", firstval): return
            if 'start page' in self._storage and not 'pages' in self._publ:
                self._publ['pages'] = "%s-%s" % (self._storage['start page'][0], firstval)
            else:
                self._storage[property] = [firstval]
        # --------------------------------------------------
        # Now other entities connected with the publiacation
        # --------------------------------------------------
        elif property == 'topic':
            for topictitle in values:
                rel = RRSRelationshipPublicationTopic()
                rel.set_entity(RRSTopic(title=topictitle))
                self._publ['topic'] = rel
        elif property == 'url':
            for link in values:
                try:
                    rel = RRSRelationshipPublicationUrl()
                    u = RRSUrl(link=link)
                except (RRSDatabaseAttributeError, RRSDatabaseEntityError, RRSDatabaseValueError):
                    return
                u['type'] = RRSUrl_type(type='publication')
                rel.set_entity(u)
                self._publ['url'] = rel
        elif property == 'keywords':
            for kw in values:
                rel = RRSRelationshipPublicationKeyword()
                rel.set_entity(RRSKeyword(title=kw))
                self._publ['keyword'] = rel
        elif property in ('author', 'editor'):
            for person in values:
                rel = RRSRelationshipPersonPublication()
                rel['editor'] = property == 'editor'
                r = self.ee.find_authors(person)
                if not r[0]: return
                rel.set_entity(r[0][0])
                rel['author_rank'] = len(self._publ['person']) + 1
                self._publ['person'] = rel
        elif property == 'reviews':
            # TODO if real reviews would be implemented in DB schema,
            # change this: add RRSReview objects into publication
            self._publ.set("review", values, strict=False)


    def _parse_meta(self, document):
        doc_meta = document.get_meta_map()
        # transform into generalized form
        for key in doc_meta:
            property = self.generalizer.generalize(key)
            if property is None: continue
            if property in self._storage:
                for val in doc_meta[key]:
                    if val not in self._storage[property]:
                        self._storage[property].append(val)
            else:
                self._storage[property] = doc_meta[key]
        # make authors and editors disjoint sets
        if 'author' in self._storage and 'editor' in self._storage:
            to_del = []
            for a in self._storage['author']:
                if a in self._storage['editor']:
                    to_del.append(a)
            for a in to_del:
                self._storage['author'].remove(a)
        # and now just set the values into real RRS objects
        for property in self._storage:
            self._add_property(property, self._storage[property])
        self._storage= {}


    def _find_local_sequence(self, header_elem, h_func):
        # lightweight version of sequencewrapper (rrslib.web.sequencewrapper)
        # targeted to repeated sequence of tags in one level of DOM - there's no
        # analysis of data regions (we already found one), just looking for data
        # records in a very straightforward (and very stupid) way.
        # @param header_elem - lxml.html.HtmlElement representing header element
        # @param h_func - heuristic function returning true/false, has to accept
        #                 one parameter - element (instance of lxml.html.HtmlElement)
        # @return tuple (records, likelihood of data)
        tags = ListedDict()
        for elem in header_elem.iterchildren():
            if elem.tag in self._omitted_tags: continue
            tags[elem.tag] = elem
        (tag, elements) = tags.item_by_longest_value()
        if len(elements[0]) < 2:
            return (None, 0.0)
        res = []
        grouped_elements = []
        for e_group in elements:
            res.extend(filter(h_func, e_group))
            grouped_elements.extend(e_group)
        return (res, float(len(res))/float(len(grouped_elements)))


    def _get_data_below_header(self, elem, hdrtext, to_be_processed):
        # Try to iter over siblings of the header element and get text
        siblings = [sib.tag for sib in elem.itersiblings()]
        # the header is abstract
        if hdrtext == 'abstract':
            txts = {}
            paragraphs = []
            par_stop = False
            for sib in elem.itersiblings():
                content = sib.text_content()
                if sib in to_be_processed:
                    par_stop = True
                if sib.tag == 'p' and len(content) > 50 and not par_stop:
                    paragraphs.append(content)
                chunk = content[0:20].lower()
                score = 1.0
                for st in self._abstract_startswith:
                    if chunk.startswith(st): score*=5.0
                score *= len(content)
                txts[score] = SimpleHTMLCleaner.clean(content)
            if paragraphs:
                self._storage[hdrtext] = [SimpleHTMLCleaner.clean(" ".join(paragraphs))]
            else:
                self._storage[hdrtext] = [ txts[max(txts.keys())] ]

        # related publications
        elif hdrtext == 'related':
            list_tags = ('ul', 'ol', 'dl')
            return # TODO
            for ltag in list_tags:
                if ltag in siblings:
                    for sib in elem.itersiblings(): pass

        # keywords
        elif hdrtext == 'keywords':
            # create function returning elements containing possible keywords
            is_keyword = lambda kw: re.search("^(([a-z]{3,}( |,)){1,3} ?)+([a-z]{3,} ?){1,3}$", \
                                    kw.text_content(), re.I) \
                                    and not re.search("[@#\$%\^&\*\(\)]", kw.text_content())
            # iter over siblings of header a try to get keywords from its children
            likelihood_to_keyword_tags = ListedDict()
            for s in elem.itersiblings():
                (kw_elems, likelihood) = self._find_local_sequence(s, is_keyword)
                if kw_elems is None: continue
                likelihood_to_keyword_tags[likelihood] = kw_elems
            if not likelihood_to_keyword_tags: return
            # if found some keywords, store them
            self._storage[hdrtext] = [kw.text_content() for kw in likelihood_to_keyword_tags[max(likelihood_to_keyword_tags.keys())][0]]

        # references
        elif hdrtext == 'references':
            pass # TODO

        # chapters ??
        elif hdrtext == 'chapters':
            pass # TODO

        # reviews?
        elif hdrtext == 'reviews':
            if hdrtext in self._storage: return
            # create function returning elements containing possible reviews
            is_review = lambda r: (len(r.text_content()) > 100) or r.tag == 'blockquote'
            probability = ListedDict()
            # iter over siblings of header a try to get reviews from its children
            for s in elem.itersiblings():
                (elems, prob) = self._find_local_sequence(s, is_review)
                if elems is None: continue
                probability[prob] = elems
            review_texts = []
            if not probability: return
            for e in probability[max(probability.keys())][0]:
                review_texts.append(SimpleHTMLCleaner.clean(e.text_content()))
                # set all the elements as "processed" to avoid further processing
                for d in e.iter():
                    d.processed = True
            self._storage[hdrtext] = review_texts


    def _parse_visibility(self, document):
        vis_map = self._get_visibility2elem_map(document.get_etree())
        if len(vis_map) < 2: return
        sorted_vis = sorted(vis_map.keys(), reverse=True)
        if len(sorted_vis) < 2: return
        to_be_processed = None
        while 42: #:)
            to_be_processed = []
            for i in xrange(0, len(sorted_vis)):
                if sorted_vis[i] < self.headercoef: continue
                to_be_processed.extend(vis_map[sorted_vis[i]])
            if len(to_be_processed) < 2:
                self.headercoef -= 0.5
            else: break
        # storage for possible titles
        possible_titles = ListedDict()
        # loop over all headers (elements containing very visible texts)
        for elem in to_be_processed:
            # get cleaned text content of the tag
            txt = SimpleHTMLCleaner.clean( elem.text_content() )
            # generalize: maybe it is something useful
            hdrtext = self.generalizer.generalize(txt)
            # generalization found header beeing TITLE -> data are below header
            if hdrtext is not None:
                # found some useful header, try to get data below
                # what is below? probably sibling tags and their descendants
                self._get_data_below_header(elem, hdrtext, to_be_processed)
            # generalization wasnt successful -> maybe the header contains data
            else:
                # date?
                d = self.ee.find_published_date(txt)
                if d[0]:
                    rrsdate = d[0][0]
                    for attr in ('year', 'month'):
                        if rrsdate.get(attr) is not None:
                            self._publ[attr] = rrsdate.get(attr)
                    txt = d[1]
                # maybe title
                if len(txt.split(" ")) > 3: # probably more than three words
                    # is there a domain name in the title? So it is probably
                    # general name of the website
                    if len(self.domain) > 6 and re.search(re.escape(self.domain), txt, re.I):
                        continue

                    # preprocessing - remove standalone brackets
                    txt = re.sub("[\(\[][^\)\]]*[\)\]]+", "", txt).strip()
                    if document.name is not None and re.search(re.escape(txt), document.name, re.I):
                        possible_titles[int(self._classify_publ_title(txt, init=100))] = txt
                    elif len(txt.split(" ")) > 5:
                        possible_titles[int(self._classify_publ_title(txt, init=60))] = txt
        if possible_titles:
            titles = possible_titles[max(possible_titles)]
            if len(titles) > 1:
                title = self._get_longest_string(titles)
            else:
                title = titles[0]
            self._publ['title'] = title
            self._publ['credibility'] = max(possible_titles)
        else:
            self._publ['credibility'] = 0
        # store all new properties and their values
        for property in self._storage:
            self._add_property(property, self._storage[property])


    def _get_longest_string(self, l):
        mx = None
        maxlen = 0
        for t in l:
            if len(t) > maxlen:
                maxlen = len(t)
                mx = t
        return mx


    def _find_abstract(self, etree):
        c = Cleaner(scripts=True, javascript=True, comments=True, style=True,
                    meta=True, page_structure=False, processing_instructions=True,
                    embedded=True, frames=False, forms=True, annoying_tags=True,
                    add_nofollow=False, remove_unknown_tags=False)
        etree_copy = deepcopy(etree)
        etree_copy = c.clean_html(etree_copy)
        html = tostring(etree_copy.getroot())
        # XXX this may be probably useful, to delete all <p> tags...
        html = re.sub("</?p[^>]*>", " ", html)
        possible = []
        txts = re.findall("(?<=\>)[^>]+(?=\<)", html, re.U)
        for txt in txts:
            txt = SimpleHTMLCleaner.clean(txt)
            if len(txt) > 200:
                do_not_append = False
                for bl in self._abstract_blacklist:
                    if txt.startswith(bl):
                        do_not_append = True
                        break
                if not do_not_append:
                    possible.append(txt)
                    continue
            for st in self._abstract_startswith:
                if txt.startswith(st):
                    possible.append(txt)
                    break
        return self._get_longest_string(possible)


    def _find_unbound_entities(self, page):
        root = page.get_etree().getroot()
        # get abstract
        if not 'abstract' in self._publ:
            abst = self._find_abstract(page.get_etree())
            if abst is not None:
                self._publ['abstract'] = abst

        # find url of publication (pdf, ps, doc...)
        if 'url' not in self._publ:
            to_be_checked = []
            for (element, attribute, link, pos) in root.iterlinks():
                if re.search("(pdf|doc|odt|ps)$", link, re.I):
                    to_be_checked.append(link)
                # TODO try to get links with no suffix (queries etc.)
                # ----------------------------------------------------
                # ADD THE CODE HERE
                # ----------------------------------------------------
            if to_be_checked:
                documents = []
                mimes = self.mime_handler.start(to_be_checked)
                for link in mimes:
                    if mimes[link] in self._accepted_mime:
                        documents.append(link)
                dl = len(documents)
                doc_link = None
                if dl == 1: # exactly one link
                    doc_link = documents[0]
                elif dl != 0: # more than one
                    # try to guess out of the name of the publication
                    if 'title' in self._publ:
                        doc_link = self._most_alike_term(self._publ['title'], documents, 0.5)
                if doc_link is not None:
                    try:
                        rel = RRSRelationshipPublicationUrl()
                        u = RRSUrl(link=doc_link)
                    except (RRSDatabaseAttributeError, RRSDatabaseEntityError, RRSDatabaseValueError):
                        return
                    u['type'] = RRSUrl_type(type='publication')
                    rel.set_entity(u)
                    self._publ['url'] = rel

        # Now extract unbound entities from the plaintext.
        # Every time there is a high probability that the relationship will be
        # miss-recognitized.

        # get keywords if there are no such
        if not 'keyword' in self._publ:
            # Try to get keywords from the text. They are probably in the format:
            # Keywords: algorithm, algorithmic process, random, some other keyword
            kwre = re.search("keywords?:?[\t\n\r ]+(([a-z]{3,}( |,)){1,3} ?)+([a-z]{3,} ?){1,3}", self.pagetext, re.I)
            if kwre is not None:
                kwstr = kwre.group(0)
                kwstr = re.sub("[kK]eywords?:?[\t\n\r ]+", "", kwstr)
                keywords = [x.strip() for x in kwstr.split(",")]
                for kw in keywords:
                    rel = RRSRelationshipPublicationKeyword()
                    rel.set_entity(RRSKeyword(title=kw))
                    self._publ['keyword'] = rel


    def _parse_bibtex(self, page):
        # Parse all possible bibtex on the page.
        # At first parse plaintext of the page and try to get BibTeX string out
        # of there. Then try to find possible links fo bibtex files, download
        # them and parse them.
        bibtexpubl = self.bibtexparser.parse(self.pagetext)
        if bibtexpubl:
            pass
        # try to get .bib or .bibtex files from the page
        else:
            html_tag = page.get_etree().getroot()
            bibtex_links = set()
            for l in html_tag.iterlinks():
                if re.search("\.bib(tex)?$", l[2], re.I):
                    bibtex_links.add(l[2])
            if len(bibtex_links) == 1:
                r = self.crawler.start(bibtex_links)
                for link in bibtex_links:
                    bibtex_file = r[link]
                    if isinstance(bibtex_file, basestring):
                        bibtexpubl = self.bibtexparser.parse(bibtex_file)
                    else:
                        return
            else:
                # TODO handle more than one bibtex files???
                return
        # process found bibtex
        publ = bibtexpubl[0]
        for attr in publ:
            value = publ[attr]
            # not set, useless
            if value is None:
                continue
            # list of relationship attrs
            elif isinstance(value, list):
                for v in value:
                    self._publ[attr] = v
            # own attribute
            else:
                self._publ[attr] = value


    def extract_data(self, etree, url):
        """
        Extract all possible data about the publication from the web page.
        @param etree - parsed DOM tree of the web page (has to be instance of
                       lxml.etree._ElementTree)
        @param url - url of the web page
        @return RRSPublication object containing extracted data
        """
        assert isinstance(url, basestring)
        assert isinstance(etree, _ElementTree)
        #c = Cleaner(scripts=True, javascript=True, comments=True, style=False,
        #            meta=False, page_structure=False, processing_instructions=True,
        #            embedded=True, frames=False, forms=True, annoying_tags=False,
        #            add_nofollow=False, remove_unknown_tags=False)
        #etree = c.clean_html(etree)
        self.url = url
        self.domain = re.sub("http://(www)?", "", self.url).split(".")[0]
        self._storage= {}
        self._publ = RRSPublication()
        cleaned_etree = SimpleHTMLCleaner.clean_html(etree)
        page = HTMLDocument(cleaned_etree, url)
        self.pagetext = page.get_etree().getroot().text_content()
        # parse CSS and metadata on the page
        page.parse_document()
        # get data from <meta> tags nad convert to RRS format
        self._parse_meta(page)
        # get data on the basis of the text visbility and recognized headers
        self._parse_visibility(page)
        # and now guess :)
        self._find_unbound_entities(page)
        # and parse BibTeX
        self._parse_bibtex(page)
        return self._publ

#-------------------------------------------------------------------------------
# end of class PublicationPageExtractor
#-------------------------------------------------------------------------------

if __name__ == "__main__":
    from rrslib.web.crawler import Crawler
    from rrslib.xml.xmlconverter import Model2XMLConverter
    url = []
    #url = "http://learning.infocollections.com/ebook%202/Computer/Operating%20Systems/Linux%20&%20UNIX/Unix.Systems.Programming.Second.Edition/0130424110_ch17lev1sec11.html"
    #url = ["http://cogprints.org/2021/"]
    #url = "http://www.citeulike.org/user/cdiggins/article/1981586"
    #url.append("http://www.researchgate.net/publication/2299330_On_the_Approximate_Cyclic_Reduction_Preconditioner")
    #url.append("http://geomblog.blogspot.com/2006/05/on-algorithmization-of-science.html")
    #url = "http://www.siam.org/meetings/da03/Invited/muthu.htm"
    url = ["http://www.cs.cmu.edu/~Vit/paper_abstracts/keynote01.html"]
    #url.append("http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.80.4033&rank=3")
    #url.append("http://academic.research.microsoft.com/Publication/1864814/integrating-ontologies-into-learning-management-systems-a-case-of-czech")
    url.append("http://www.citeulike.org/user/lschiff/article/399212/")
    #url.append("http://www.coursehero.com/file/1789647/0400265/")
    url.append('http://www.citeulike.org/user/pkufranky/article/1003603')
    #url.append("http://www.amazon.ca/product-reviews/0130151572")
    c = Crawler()
    c.set_headers((
                   ('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.19) Gecko/2010040116 Ubuntu/9.04 (jaunty) Firefox/3.6'), \
                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                 ))
    result = c.start(url)
    ppe = PublicationPageExtractor()
    for u in result:
        etree = result[u]
        model = ppe.extract_data(etree, u)
        #print model
        m2xml = Model2XMLConverter()
        m2xml.convert(model)

