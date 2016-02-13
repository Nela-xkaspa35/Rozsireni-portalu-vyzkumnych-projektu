#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
This library provides some low-level operations with html documents (like
entity decoding or source cleaning) and also some fundaments of web framework
in rrslib (class HTMLDocument).
"""

__modulename__ = "htmltools"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__  = "$31.3.2011 18:01:11$"

import htmlentitydefs
import re
import string

from lxml.etree import ElementTree
from lxml.html import fromstring, tostring

from rrslib.web.csstools import CSSParser
from rrslib.web.lxmlsupport import persist_ElementTree
from rrslib.others.pattern import cached, lazy
from rrslib.classifiers.language import LanguageIdentifier
from rrslib.extractors.normalize import Normalize


class HtmlEntityDecoder(object):
    """
    HtmlEntityDecoder decodes HTML named and numbered entities to text.
    """

    def __init__(self):
        # pattern to recognize html entity
        self.pattern = re.compile(r'&(#?)(x?)(\w+);')
        # dictionary translating usual entities
        self.name2text = {'apos': '\'', 'nbsp': ' ', 'mdash': '-', 'ndash': '-',
                          'ldquo': '\"', 'rdquo': '\"', 'lsquo': '\'',
                          'rsquo': '\'', 'lsaquo': '<', 'rsaquo': '>'}

    def _substitute_entity(self, match):
        """
        Get the entity and return character or unicode
        """
        entity_name = match.group(3)
        try:
            # get named entities
            entdef = htmlentitydefs.entitydefs[entity_name]
            if entdef.startswith("#?"):
                entdef = entdef[2:-1]
            #entdef = self.name2text[entity_name]
        except KeyError:
            entdef = entity_name
        try:
            # convert numbered entity
            entdef = unichr(int(entdef))
        except: pass
        return entdef


    def decode_htmlentities(self, string):
        """
        Returns string with decoded entities
        """
        dec_string = self.pattern.sub(self._substitute_entity, string, re.U)
        return dec_string

#-------------------------------------------------------------------------------
# End of class HtmlEntityDecoder
#-------------------------------------------------------------------------------


class SimpleHTMLCleaner(object):
    """
    HTMLCleander provides simple methods for cleaning text and HTML code.
    It also normalizes some national characters and HTML entities.

    For improved html-cleaning use lxml-library methods.
    """
    @classmethod
    def clean(self, text):
        """
        Cleans text.
        """
        if text == None: return None
        plaintext = re.sub('<[^>]+>', ' ', text)  # smaze tagy
        plaintext = re.sub('['+string.whitespace+'\xc2\xa0]+', ' ', plaintext)    # smaze tabulatory a odradkovani
        clear_plaintext = re.sub('[ ]+', ' ', plaintext) # smaze dlouhe mezery
        return clear_plaintext.rstrip(' \"\')(').lstrip(' \"\')(')


    @classmethod
    def clean_html(self, elemtree):
        """
        Cleans HTML page in format lxml.etree._ElementTree. This method decodes
        HTML entities and translates national characters into normal form.
        Warining! This method creates new ElementTree instead of the old one!
        """
        ed = HtmlEntityDecoder()
        html = tostring(elemtree)
        html = ed.decode_htmlentities(html)
        html = Normalize.translate_national(html)
        html = re.sub("<[bB][rR][^>]*\/?>", " ", html)
        return ElementTree( fromstring(html) )


    @classmethod
    def contains_text(self, tag):
        """
        Testing if tag contains some useful text (non-whitechar)
        """
        try:
            if isinstance(tag, basestring):
                txt = tag
            else:
                txt = tag.text
            if re.search("[\w]+", txt, re.I): return True
        except:
            return False


#-------------------------------------------------------------------------------
# End of class SimpleHTMLCleaner
#-------------------------------------------------------------------------------


class HTMLDocument(object):
    """
    Fundamental class for rrslib web framework. HTMLDocument provides API for
    visibility-driven manipulation - added new attribute "style" to each element
    of the tree. This style is type CSSStyle and represents result of parsed
    cascade styles on the page and in external files.

    HTMLDocument uses persistent-tree API for lxml.

    This class also provides methods for high-level page operations like:
     - frame checking
     - metadata parsing
     - navigation storage (should parse the page implicitly)
    """
    def __init__(self, elemtree, url):
        # object tree representing this document
        self._lxmletree = elemtree
        # css parser parses extern and inline css declarations on page
        self.cssparser = CSSParser()

        # metadata, additional information about document
        self.frames = []
        self.url = url
        self._meta = {}

        # content
        self.navigation = {}
        self.name = None


    def _normalize_meta_property(self, property):
        for delim in (".", ":"):
            if delim in property:
                property = property.split(delim)[1]
        if property[0].isupper():
            property = property.lower()
        # classify uppper letters
        firstupper = property[0].isupper()
        middleupper = not property[1:].islower()
        if firstupper and not middleupper:
            property = property.lower()
        elif middleupper:
            buff = []
            for i, letter in enumerate(property):
                if i == 0:
                    buff.append(letter.lower())
                    continue
                if letter.isupper():
                    buff.append(' ')
                buff.append(letter.lower())
            property = "".join(buff)
        return property


    @lazy
    def _parse_meta(self):
        title = self._lxmletree.find('.//title')
        if title is not None:
            self.name = title.text
        meta = self._lxmletree.findall('.//meta[@content]')
        for tag in meta:
            content = tag.get("content")
            name, httpequiv, property = tag.get("name"), tag.get("http-equiv"), tag.get("property")
            if name is not None:
                name = self._normalize_meta_property(name)
                if name == 'keywords':
                    self._meta[name] = [x.strip() for x in content.split(",")]
                else:
                    if name in self._meta:
                        if content not in self._meta[name]:
                            self._meta[name].append(content)
                    else:
                        self._meta[name] = [content]
            elif httpequiv is not None:
                httpequiv = httpequiv.lower()
                if httpequiv == 'content-type':
                      contenttype, charset = content.split(";")
                      self._meta[httpequiv] = contenttype
                      self._meta['charset'] = charset.split("=")[1]
                else:
                    self._meta[httpequiv] = content
            elif property is not None:
                property = self._normalize_meta_property(property)
                if property in self._meta:
                    if content not in self._meta[property]:
                        self._meta[property].append(content)
                else:
                    self._meta[property] = [content]


    def get_meta(self, name):
        self._parse_meta()
        try:
            return self._meta[name]
        except KeyError:
            return None


    def get_meta_map(self):
        self._parse_meta()
        return self._meta


    @lazy
    def parse_document(self):
        """
        Parse the whole HTML document on the basis of lxml.etree.ElementTree.
        """
        # use persistent lxml.etree_ElementTree API (rrslib extension)
        persist_ElementTree(self._lxmletree)
        # Parse css
        self.cssparser.parse(self._lxmletree, self.url)
        # parse metadata
        self._parse_meta()


    @cached
    def get_language(self):
        l = LanguageIdentifier()
        return l.identify(self.text_content())

    @cached
    def text_content(self):
        return self._lxmletree.getroot().text_content()


    def get_element_visibility(self, elem):
        """
        Returns integer representing visibility of the element's text.
        """
        return elem.style.get_visibility()

    @cached
    def get_frames(self):
        """
        If page contains frames, returns their urls (from "src" attribute)
        @return list of frame's URL's or None if no frames on the page
        """
        # get all frames on the page
        f = []
        try:
            frames = self._lxmletree.findall('//frameset/frame')
            frames.extend(self._lxmletree.findall('//iframe'))
        except: return None
        # nothing found, it is noframe page
        if not frames: return None
        # frames found, get URLs from them
        for frame in frames:
            # make frame URLs absolute
            if self.url is not None:
                base = self.url
                basesplit = urlsplit(self.url)
                if re.match("/[^.]*[^/]$", basesplit[2], re.I):
                    base = self.url + "/"
                frame.make_links_absolute(base)
            # URL is in src attribute
            f.append(frame.get('src'))
        return f # list of frames URLs


    def add_menu_item(self, text, link):
        self.navigation[text] = link

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_url(self):
        return self.url

    def get_menu(self):
        return self.navigation

    def get_etree(self):
        return self._lxmletree

    def __str__(self):
        return "<"+__modulename__+".HTMLDocument url='" + self.url + "'>"


# ------------------------------------------------------------------------------
# end of class HTMLDocument
# ------------------------------------------------------------------------------
