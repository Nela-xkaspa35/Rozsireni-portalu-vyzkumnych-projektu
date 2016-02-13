#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sequencewrapper library offers methods for parsing HTML pages on basis of searching
for similar records on page - these records could be for example: items in product
list in e-shop, references on publication list, items on e-bay, in general all
pages with formatted text, structure and repeating sequences.

The main algorithm is based on searching for equivalent tags (identical tag label)
which are in the same depth. The longest sequence is considered to be most valuable.

HTMLSequenceWrapper implements recongnition of headers on basis of visual importance
of font (parsing CSS, font-affecting tags etc.). The bigger and bolder, the more
important the text is.



Representative output of HTMLSequenceWrapper.wrap() method:

<?xml version='1.0' encoding='utf-8'?>
<document base="http://bionum.cs.purdue.edu/p.html" title="Publication List">
  <menu/>
  <sequence-area>
    <header visibility="6.48">General</header>
    <entry>
      <text>KSSM05 L.V. Kale, K. Schulten, R.D. Skeel, G. Martyna, M. Tuckerman,
      J.C. Phillips, S. Kumar, and G. Zheng, Biomolecular modeling using parallel
      supercomputers , In S. Aluru, editor, Handbook of Computational Molecular
      Biology pages 34-1 to 34-43, Chapman &amp; Hall/CRC Press, 2005.</text>
      <chunks>
        <chunk visibility="2.56">KSSM05</chunk>
        <chunk visibility="1.0">Biomolecular modeling using parallel supercomputers</chunk>
        <chunk visibility="2.0">Handbook of Computational Molecular Biology</chunk>
      </chunks>
    </entry>
    ...
    ...
    <entry>
      <text>BKSS94 J. A. Board Jr., L. V. Kale, K. Schulten, R. D. Skeel and T.
      Schlick, Modeling Biomolecules: Larger Scales, Longer Durations , IEEE
      Computational Science &amp; Engineering , 1 :19-30, 1994.</text>
      <chunks>
        <chunk visibility="2.56">BKSS94</chunk>
        <chunk visibility="1.0">Modeling Biomolecules: Larger Scales, Longer Durations</chunk>
        <chunk visibility="2.0">IEEE Computational Science &amp; Engineering</chunk>
        <chunk visibility="2.56">1</chunk>
      </chunks>
    </entry>
  </sequence-area>
  <sequence-area>
    <header visibility="6.48">Transition Paths, Free Energies</header>
    <entry>
      <text>Skee09b R. D. Skeel, Two-Point Boundary Value Problems for Curves:
      The Case of Minimum Free Energy Paths in T. E. Simos, G. Psihoyios, and C.
      Tsitouras, editors, Numerical Analysis and Applied Mathematics: International
      Conference on Numerical Analysis and Applied Mathematics 2009 , volume 1168/1 ,
      pages 29-31, 2009. corrected PDF</text>
      <chunks>
        <chunk visibility="2.56">Skee09b</chunk>
        <chunk visibility="1.0">Two-Point Boundary Value Problems for Curves:
        The Case of Minimum Free Energy Paths</chunk>
        <chunk visibility="2.0">Numerical Analysis and Applied Mathematics:
        International Conference on Numerical Analysis and Applied Mathematics 2009</chunk>
        <chunk visibility="2.56">1168/1</chunk>
        <chunk visibility="2.0">corrected</chunk>
        <chunk visibility="1.0" link="http://bionum.cs.purdue.edu/09bSkeeCORR.pdf">PDF</chunk>
      </chunks>
    </entry>
  </sequence-area>
  ...
</document>
"""

################################################################################
# module options
################################################################################

__modulename__ = "sequencewrapper"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$7-June-2010 11:37:11$"



import re # regular expressions
from lxml import etree # and of cource our favorite lxml.etree :)

# rrslib
from rrslib.web.csstools import CSSStyle, CSSStyleError
from rrslib.web.htmltools import SimpleHTMLCleaner, HTMLDocument

try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")



class TextChunk(object):
    """
    TextChunk represents one piece of textual part of recognized record. This is
    mainly text inside **ONE** tag. TextChunk contains style (instance of FontStyle),
    it may contain link (<a href="foo"></a>), tag of which text is kept here,
    comment (<a title="foo"></a>) and of course text of the tag.

    For future usage: there could be inserted semantics (textual) into param $sem
    in constructor.
    """

    def __init__(self, text=None, style=None, link=None, tag=None, sem=None, comment=None):
        self.link = link
        self.style = style
        self.text = text
        self.tag = tag
        self.comment = comment
        # TODO FUTURE USE - while harvesting data from table, we can reach named
        # entity semantics by <th> header or in the first row
        self.semantic = sem


    def get_text(self):
        return self.text


    def get_link(self):
        return self.link


    def get_style(self):
        return self.style


    def get_tag(self):
        return self.tag


    def get_comment(self):
        return self.comment


    def set_comment(self, comment):
        self.comment = comment


    def set_style(self, style):
        if not isinstance(style, CSSStyle):
            raise CSSStyleError("Attribute style has to be instance of FontStyle")
        self.style = style


    def set_link(self, link):
        self.link = link


    def set_text(self, text):
        self.text = text


    def set_tag(self, tag):
        self.tag = tag


    def __str__(self):
        return "<"+__modulename__+".TextChunk instance " + self.text + " " + str(self.style)+ ">"

# ------------------------------------------------------------------------------
# end of class TextChunk
# ------------------------------------------------------------------------------


class HTMLSequenceWrapperRecord(object):
    def __init__(self, element, url, mintextlen=10):
        self.cleaner = SimpleHTMLCleaner()
        self.mintextlen = mintextlen
        self.elem = element
        self.url = url

        # the whole text
        self.text = self.elem.text_content()
        self.text = self.cleaner.clean(self.text)

        self.chunks = []
        self.__extract_chunks(self.elem)


    def has_value(self):
        if self.cleaner.contains_text(self.text) == False:
            return False
        return len(self.text) > self.mintextlen


    def get_chunks(self):
        return self.chunks


    def get_text(self):
        return self.text


    def _handle_elem(self, elem):
        if elem.text == None: return None
        if not self.cleaner.contains_text(elem): return None
        # new chunk
        chunk = TextChunk()

        ## extracting links
        if elem.get('href') != None:
            chunk.set_link(elem.get('href'))
        # extracting 'title' atribute in anchor
        if elem.tag == 'a' and elem.get('title') != None:
            chunk.set_comment(elem.get('title'))

        # extracting text
        txt = elem.text_content()
        chunk.set_text(self.cleaner.clean(txt))

        # setting style
        fs = elem.style
        chunk.set_style(fs)
        chunk.set_tag(elem.tag)
        return chunk


    def __extract_chunks(self, elem):
        thischunk = self._handle_elem(elem)
        if thischunk != None:
            self.chunks.append(thischunk)
        for child in elem.iterchildren():
            self.__extract_chunks(child)


    def __str__(self):
        return "<"+__modulename__+".HTMLSequenceWrapperRecord instance " + self.text + " >"


# ------------------------------------------------------------------------------
# end of class HTMLSequenceWrapperRecord
# ------------------------------------------------------------------------------


class HTMLSequenceWrapperRegion(object):
    def __init__(self):
        self.records = []
        self.name = None
        self.headerstyle = None


    def add_record(self, rec):
        if not isinstance(rec, HTMLSequenceWrapperRecord):
            raise AttributeError("Record has to be instance of HTMLSequenceWrapperRecord")
        self.records.append(rec)

    def is_empty(self):
        return len(self.records) == 0

    def set_name(self, name):
        self.name = name

    def set_header_style(self, style):
        if not isinstance(style, CSSStyle):
            raise CSSStyleError("Attribute style has to be instance of FontStyle")
        self.headerstyle = style

    def _manual_process_page(self):
        return self.records

    def get_name(self):
        return self.name

    def get_header_style(self):
        return self.headerstyle

    def __str__(self):
        return "<"+__modulename__+".HTMLSequenceWrapperRegion " + str(self.name) + ">"

# ------------------------------------------------------------------------------
# end of class HTMLSequenceWrapperRegion
# ------------------------------------------------------------------------------


class ParsedHTMLDocument(HTMLDocument):
    """
    This class represents result of sequencewrapper. It contains parsed regions
    and records harvested from the page.
    """
    def __init__(self, elemtree, url):
        HTMLDocument.__init__(self, elemtree, url)
        self.regions = []

    def add_region(self, region):
        if not isinstance(region, HTMLSequenceWrapperRegion):
            raise AttributeError("Region has to be instance of HTMLSequenceWrapperRegion")
        self.regions.append(region)

    def get_regions(self):
        return self.regions

    def __str__(self):
        return "<"+__modulename__+".ParsedHTMLDocument url='" + self.url + "' found_regions=" + str(len(self.regions)) + ">"

# ------------------------------------------------------------------------------
# end of class ParsedHTMLDocument
# ------------------------------------------------------------------------------


class HTMLSequenceWrapper(object):
    """
    HTMLSequenceWrapper is an itelligent system for pattern and repeating
    sequence recognition on web pages. Input of this algorithm is element tree
    object (lxml.etree._ElementTree) and output is instance of ParsedHTMLDocument.

    The sequencewrapper parses element tree to get most valuable repeating sequence
    which is supposed to be data record. It also finds out regions.
    """

    # list of important terms to get menu.
    _menu = ('[CK]onta[ck]t', 'Publi[ck]', 'Blog', 'Links', 'About', 'Home', 'News?', \
             'Event', 'Research', 'Index', 'FAQ', 'People', 'Overview', 'Profile', \
             'Community', 'Download')

    # this list prolly shouldnt be here, but in some higher class what uses
    # HTMLSequenceWrapper to get page structure and semantics
    _semantic_tags = {'dfn': 'Definition Term',            # <dfn>
                      'address': 'Address',                # <address>
                      'em': 'Emphasis',                    # <em>
                      'strong': 'Strong Text',             # <strong>
                      'ins': 'Inserted',                   # <ins>
                      'del': 'Delete',                     # <del>
                      'cite': 'Citation',                  # <cite>
                      'code': 'Computer code text',        # <code>
                      'samp': 'Sample computer code text', # <samp>
                      'kbd': 'Keyboard text',              # <kbd>
                      'var' : 'Variable'}                  # <var>

    def __init__(self, childcoef=7.0, headercoef=4.0, mintextlen=10, omitted_tags=('option', 'br', 'select', 'form')):
        self.sequences = {}
        self.childcoef = childcoef
        self.headercoef = headercoef
        self.mintextlen = mintextlen
        self.omitted_tags = omitted_tags

        self.records = []
        self.cleaner = SimpleHTMLCleaner()


    def _append(self, elem, depth):
        if str(elem.tag) == '<built-in function Comment>': return
        key = elem.tag + "_" + str(depth)
        if not key in self.sequences:
            self.sequences[key] = [elem]
        else:
            self.sequences[key].append(elem)


    def _recurse(self, elem, depth):
        self._append(elem, depth)
        for child in elem.iterchildren():
            self._recurse(child, depth+1)


    def _get_most_freq(self, seqdict, position=1):
        reversed_entries = {}
        for k in seqdict:
            reversed_entries[len(seqdict[k])] = seqdict[k]
        ordered = sorted(reversed_entries.keys(), reverse=True)
        # FILTERING TAGS
        # filter non-usable tags like <option>, <br> or <form>
        for i in range(len(ordered)):
            mf = reversed_entries[ordered[(position-1)+i]]
            if mf[0].tag not in self.omitted_tags:
                break
        return mf


    def _find_nearest_parent(self, elems):
        parents = {}
        for elem in elems:
            parent = elem.getparent()
            if parent == None: continue
            if parent.tag not in parents:
                parents[parent.tag] = [parent]
            else:
                if not parent in parents[parent.tag]:
                    parents[parent.tag].append(parent)
        mf = self._get_most_freq(parents)
        #del parents
        return mf


    def _isbodyelem(self, elem):
        return elem.tag != None and elem.tag == 'body'


    def _sift(self, elems):
        sift = True
        while sift:
            parents = self._find_nearest_parent(elems)
            if self._isbodyelem(parents[0]): break
            sift = len(elems) < self.childcoef * len(parents)
            if sift: elems = parents
        self.sifted_first = elems[0]
        # improve speed by converting list to set
        try:
            return set(elems)
        except MemoryError:
            return elems


    def _find_regions(self):
        # delete previously found data
        self.regions = []
        area = HTMLSequenceWrapperRegion()
        for elem in self.elemtree.getroot().iterdescendants():
            _style = elem.style
            if _style is None:
                _style = CSSStyle()
            # we consider it to be a header if visibility self.headercoef
            if _style.get_visibility() >= self.headercoef:
                if not area.is_empty():
                    self.regions.append(area)
                    area = HTMLSequenceWrapperRegion()
                area.set_name(self.cleaner.clean(elem.text))
                area.set_header_style(_style)
            if elem in self.found_entries:
                rec = HTMLSequenceWrapperRecord(elem, self.url, self.mintextlen)
                if not rec.has_value(): continue
                area.add_record(rec)
        if not area.is_empty():
            self.regions.append(area)


    def _find_menu(self, elemtree):
        _anchors = self.elemtree.findall('.//a[@href]')
        menuanchors = []
        for a in _anchors:
            if a.text != None:
                for menuitem in HTMLSequenceWrapper._menu:
                    if re.search(menuitem, a.text, re.I):
                        menuanchors.append(a)
                        break
        if not menuanchors: return
        # sift the menu with a different child coeficient
        coef = self.childcoef
        self.childcoef = 3.0
        _menuitems = self._sift(menuanchors)
        self.childcoef = coef
        # get closest parent for all navigation items
        menu_reg = self._find_nearest_parent(_menuitems)
        _links = menu_reg[0].findall('.//a[@href]')
        for tag in _links:
            if tag == None: continue
            text = self.cleaner.clean(tag.text)
            if text == None: continue
            # bad heuristics, isn't it?
            if len(text) > 50:
                self.menu = {}
                return
            self.doc.add_menu_item(text, tag.get('href'))


    #---------------------------------------------------------------------------
    ## checking unbalanced - wrap_h() methods
    #---------------------------------------------------------------------------
    def _unbalanced_chunk_to_record_ratio(self):
        chunks, records = 0, 0
        for reg in self.regions:
            for rec in reg._manual_process_page():
                records += 1
                chunks += len(rec.get_chunks())
        try:
            return float(chunks)/float(records) < self.unbalanced_chunk_ratio
        except ZeroDivisionError:
            return True


    def _unbalanced_record_to_region_ratio(self):
        try:
            return (float(sum([len(reg._manual_process_page()) for reg in self.regions])) / \
                   float(len(self.regions))) < self.unbalanced_record_ratio
        except ZeroDivisionError:
            return True


    def _high_variablilty_of_chunk_count(self):
        chunks = []
        for reg in self.regions:
            for rec in reg._manual_process_page():
                if sum(chunks) == 0 or len(chunks) == 0 or \
                   len(rec.get_chunks()) > 3*(float(sum(chunks))/float(len(chunks))):
                    chunks.append( len(rec.get_chunks()) )
        aver = float(sum(chunks))/float(len(chunks))
        base = 0
        for x in chunks:
            base += (x - aver)**2
        base /= len(chunks)
        return base > aver


    #---------------------------------------------------------------------------
    # Public methods
    #---------------------------------------------------------------------------

    def wrap_h(self, elemtree, url):
        """
        Heuristical version of wrap() method. Warning: this method doesnt produce
        100% correct result!! And also this method runs longer than wrap() cause
        of repeating parsing sequences.

        TODO: consider clustering methods.
        """
        if not isinstance(elemtree, etree._ElementTree):
            raise TypeError("ElementTree has to be type lxml.etree._ElementTree")
        self.url = url
        self.doc = ParsedHTMLDocument(elemtree, url)
        # parse html document, css on page and in extern *.css files
        # this also makes all links absolute
        self.doc.parse_document()
        # store element tree
        self.elemtree = self.doc.get_etree()

        # recurse over tree
        self._recurse(self.elemtree.getroot(), 1)
        # get most frequented tag
        mf = self._get_most_freq(self.sequences)

        # learn
        satisfying_result_found = False
        # setting up average values of coeficients
        self.childcoef = 7.0
        self.headercoef = 4.0
        self.mintextlen = 40
        self.unbalanced_chunk_ratio = 2.0
        self.unbalanced_record_ratio = 3.0
        iterations = 0
        while not satisfying_result_found:
            iterations += 1
            if iterations > 100: break
            # push it up to get parent tags, they could be record-keepers
            self.found_entries = self._sift(mf)

            # find data regions
            self._find_regions()
            # if we found only one region with one record, its probably a mistake
            # so we have to decrease childcoef
            if len(self.regions) == 1 and len(self.regions[0].records) == 1:
                self.childcoef -= 1.5
                self.headercoef -= 1.0
            elif self._unbalanced_chunk_to_record_ratio():
                self.childcoef += 2.0
                self.headercoef += 0.5
                self.unbalanced_chunk_ratio -= 0.2
            elif self._unbalanced_record_to_region_ratio():
                self.headercoef += 1.0
                self.childcoef -= 0.5
                self.unbalanced_record_ratio -= 0.4
            elif self._high_variablilty_of_chunk_count():
                self.childcoef += 1.0
                self.mintextlen += 10
            else:
                satisfying_result_found = True
        # find navigation on page
        self._find_menu(self.elemtree)

        for reg in self.regions:
            self.doc.add_region(reg)
        #remember last url
        self.last_url = url
        # return parsed document
        return self.doc


    def wrap(self, elemtree, url):
        """
        Main method. Parses html page and searches for repeated sequences in
        element tree. Returns instance of HTMLDocument.
        """
        if not isinstance(elemtree, etree._ElementTree):
            raise TypeError("ElementTree has to be type lxml.etree._ElementTree")
        self.url = url
        self.doc = ParsedHTMLDocument(elemtree, url)
        # parse html document, css on page and in extern *.css files
        # this also makes all links absolute
        self.doc.parse_document()
        # store element tree
        self.elemtree = self.doc.get_etree()
        # recurse over tree
        self._recurse(self.elemtree.getroot(), 1)
        # get most frequented tag
        mf = self._get_most_freq(self.sequences)
        # push it up to get parent tags, they could be record-keepers
        self.found_entries = self._sift(mf)
        # find data regions
        self._find_regions()
        # find navigation on page
        self._find_menu(self.elemtree)

        for reg in self.regions:
            self.doc.add_region(reg)

        try:
          self.doc.set_name(self.elemtree.find('.//title').text)
        except AttributeError:
          pass

        #remember last url
        self.last_url = url

        # return parsed document
        return self.doc


    def _make_xml(self):
        """
        Constructs xml tree containing result of wrapping.
        """
        self.xmldocument = etree.Element("document")
        self.xmldocument.set("base", str(self.doc.get_url()))
        self.xmldocument.set("title", unicode(self.doc.get_name()))

        # add menu if available
        self.xmlmenu = etree.SubElement(self.xmldocument, "menu")
        navigation = self.doc.get_menu()
        for menuitem in navigation:
            menuitemxml = etree.SubElement(self.xmlmenu, "menuitem")
            menuitemxml.text = unicode(menuitem)
            menuitemxml.set("link", unicode(str(navigation[menuitem])))

        # add data regions
        for reg in self.regions:
            self.xmlsequence = etree.SubElement(self.xmldocument, "sequence-area")
            header = etree.SubElement(self.xmlsequence, "header")
            if reg.get_header_style() != None:
                header.set("visibility", unicode(str(reg.get_header_style().get_visibility())))
            header.text = unicode(reg.get_name())

            # add records of the region
            for r in reg._manual_process_page():
                item = etree.SubElement(self.xmlsequence, "entry")
                textxml = etree.SubElement(item, "text")
                textxml.text = unicode(r.get_text())
                chunksxml = etree.SubElement(item, "chunks")

                # add chunks
                for chunk in r.get_chunks():
                    chxml = etree.SubElement(chunksxml, "chunk")
                    chxml.text = unicode(chunk.get_text())
                    # show visibility
                    if chunk.get_style() != None:
                        chxml.set("visibility", unicode(str(chunk.get_style().get_visibility())))
                    if chunk.get_link() != None:
                        chxml.set("link", unicode(chunk.get_link()))
                    # handle tag
                    if chunk.get_tag() != None:
                        tg = chunk.get_tag()
                        if tg in HTMLSequenceWrapper._semantic_tags:
                            tg = HTMLSequenceWrapper._semantic_tags[tg]
                            chxml.set("logical", unicode(str(tg)))
                    # handle comments
                    if chunk.get_comment() != None:
                        try:
                            chxml.set("comment", unicode(str(chunk.get_comment()), encoding='utf-8'))
                        except UnicodeEncodeError:
                            try:
                                chxml.set("comment", unicode(chunk.get_comment(), encoding='utf-8'))
                            except TypeError:
                                chxml.set("comment", chunk.get_comment())



    def get_xml(self):
        """
        Returns xml of result in string format.
        """
        self._make_xml()
        # return the whole xml tree in string format
        return etree.tostring(self.xmldocument,
                              xml_declaration=True,
                              pretty_print=True,
                              encoding='utf-8')

    def get_etree(self):
        """
        Returns xml in lxml.etree.ElementTree object.
        """
        self._make_xml()
        return self.xmldocument


# ------------------------------------------------------------------------------
# end of class HTMLSequenceWrapper
# ------------------------------------------------------------------------------


if __name__ == '__main__':
    from rrslib.web.crawler import Crawler
    sp = HTMLSequenceWrapper(childcoef=5.0, headercoef=3.0, mintextlen=20)

    c = Crawler()
    #urls = ['http://www.ualberta.ca/~bhan/publ.htm']
    #urls = ['http://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=1&lang=1']
    urls = ['http://kaminari.scitec.kobe-u.ac.jp/pub_en.html',
            'http://www.cis.uab.edu/sprague/',
            'http://www2.lifl.fr/~carle/old/mabib.htm',
            'http://www.poli.usp.br/p/fabio.cozman/',
            'http://www.cs.washington.edu/homes/weld/pubs.html',
            'http://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=1&lang=1'
           ]
    #urls = ['https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=2&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=3&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=4&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=5&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=6&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=7&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=8&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=9&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=10&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=11&lang=1', 'https://www.vutbr.cz/index.php?page=obsah_publikace&wapp=portal&parent=3&tail=3&str=12&lang=1']

    #urls = ['http://www.cs.princeton.edu/~schapire/publist.html']
    #urls = ['http://bionum.cs.purdue.edu/p.html']
    #urls = ['http://www.awissenet.eu/publications.aspx']
    #urls = ['http://www.fit.vutbr.cz/~smrz/pubs.php.en']
    #urls = ['http://dbis-group.uni-muenster.de/conferences/?searchTerm=&sortBy=start&sortDirection=&dateRange=previous&button_search=Search']
    #urls = ['http://www.ws-i.org/deliverables/']
    #urls = ['http://ce.et.tudelft.nl/~george/publications/publications.html']
    #urls = ['http://www.isi.edu/~johnh/PAPERS/index.html']
    #urls = ['http://www.chimie.ens.fr/hynes/publications.php']
    urls = ['http://www.fit.vutbr.cz/~smrz/pubs.php']
    c.set_headers((
                   ('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.19) Gecko/2010040116 Ubuntu/9.04 (jaunty) Firefox/3.0.19'), \
                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                 ))
    pages = c.start(urls)
    for u in urls:
        d = sp.wrap_h(pages[u], u)
        print sp.get_xml()


