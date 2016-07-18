#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module separsers contains parsers of web search engines, which creates API for
easy information retrieval and comfortable processing of obtained data.
"""

__modulename__ = "separsers"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$18-March-2011 22:22:47$"


# load core libraries
import re
import string

# load element tree libs
from lxml import etree
import lxml.html as lh
import StringIO

# load rrs libraries
from crawler import Crawler
from rrslib.web.httptools import url_safe

# SE = search engine

class _DefaultSearchEngineParser:
    """
    Parent class of all SE parsers.
    """
    def __init__(self):
        self.rlist = []
        self.xmlresult = None
        self.resultset = None
        self.totalhits = 0


    def get_tree(self):
        """
        Return results in xml format as lxml.ElementTree object.
        """
        return self.xmlresult


    def get_list(self):
        """
        Get results in python data structure.
        """
        return self.rlist


    def get_xml(self):
        """
        Return result in xml format as a string.
        """
        return etree.tostring(self.xmlresult,
                              xml_declaration=True,
                              pretty_print=True,
                              encoding='utf-8')


    def _genxmltree(self):
        """
        Generate xml output in lxml.ElementTree object. Returns nothing.
        """
        rlen = len(self.rlist)
        # add metadata
        self.resultset.set("totalhits", str(self.totalhits))
        self.xmlresult.set("responsecode", "200")

        # loop over dictionary and store data into xml
        for item in self.rlist:
            # inovke result constructor <result>
            r = etree.SubElement(self.resultset, "result")
            r.set("position",str(item['rank']))
            # add <title> tag
            title = etree.SubElement(r, "title")
            title.text = item['title']
            # add <abstract> tag
            abstr = etree.SubElement(r, "abstract")
            abstr.text = item['abstract']
            # add <url> tag
            url = etree.SubElement(r, "url")
            url.text = item['url']

#-------------------------------------------------------------------------------
# end of class DefaultSearchEngineParser
#-------------------------------------------------------------------------------


class AltaVistaParser(_DefaultSearchEngineParser):
    def __init__(self):
        # xml output storage
        self.xmlresult = etree.Element("altavistasearchresponse")
        self.resultset = etree.SubElement(self.xmlresult, "resultset_web")

        # storage
        self.rlist = []

        # result count
        self.totalhits = 0

        # altavista query analyse
        self.altavista = 'http://www.altavista.com/web/results?itag=ody'
        self.qquery = '&q=' # query we are searching for
        self.qparams = '&kgs=0&kls=0' # additional parameters
        self.qcount = '&stq=' # count of results we want: 0 = 1-10; 10 = 11-20 etc.



    def _urlhexaconvert(self,hex_url):
        """
        Convert hexa characters to ASCII
        """
        # pattern to recognize hexadecimal characer
        pattern = re.compile(r'(?<=%)[0-9a-fA-F]{2}')
        chr_url = pattern.sub(self._substitute_hex, hex_url)
        return re.sub('%','', chr_url)


    def _substitute_hex(self, hexa):
        """
        Helper method: get hex and return ascii character
        """
        return chr(int(hexa.group(0), 16))


    def _get_alta_link(self,link):
        """
        Harvest link from special type of altavista links: http://fooooo**http://foo.bar.com
        """
        splitted = string.split(link, "**")
        try: return self._urlhexaconvert(splitted[1])
        except: return None


    def get_altavista_query(self, query, page=1):
        """
        Make AltaVista url query (URL for GET request).
        """
        if type(query) != str:
            raise AttributeError("get_altavista_query requires query of string type.")
        query = self._clean_query(query)
        if page < 1: page = 1
        stq = (int(page) - 1) * 10
        url = self.altavista + self.qquery + str(query) + self.qparams + self.qcount + str(stq)
        return url_safe(url)


    def _clean_query(self,q):
        """
        Clean query. Translate spaces to %20, ampersands, clean spaces in the
        beginning and in the end of the query.
        """
        q = q.strip()
        q = re.sub('[ ]+', '+', q)
        q = q.rstrip("+").lstrip("+")
        return q


    def parse(self, tree, genxml=True):
        """
        Main method for searching. Invokes crawler and uses it if needed. If
        AltaVista returns less results, than required, method returns maximal
        amount of results possible.
        """
        if type(tree) != etree._ElementTree:
            raise AttributeError("search() method requires etree._ElementTree object as tree")
        # clean previous results:
        self.rlist = []

        blocks = tree.findall('//ol')[0]
        self.rec = {}
        for i, li in enumerate(blocks):
            self.rec['title'] =  li[0][0][0].text_content()
            self.rec['abstract'] = li[0][1].text_content()
            self.rec['url'] = self._get_alta_link(li[0][0][0][0].get('href'))
            self.rec['rank'] = i + 1
            self.rlist.append(self.rec)
            self.rec = {}

        if genxml:
            self._genxmltree()

#-------------------------------------------------------------------------------
# end of class AltaVistaParser
#-------------------------------------------------------------------------------


class YahooBossParser(_DefaultSearchEngineParser):
    """
    Class YahooBossParser provides simple API to wrapping results of
    boss.yahooapis.com search engine API. From results deletes useless tags
    i.e.: <b>, <br> etc.

    YahooBossParser is an ancester of DefaultSearchEngineParser class.
    """
    def __init__(self):
        # yahoo boss url query
        self.yparams = '&format=xml&type=html&count='
        self.ykey = 'appid=pELZhdHV34FgmbRCnWHvOzV1kJtKUwDGa016syd8VIW365v4jkGTpjFFHIoiCwFpOP2Y'
        self.ybossurl = 'http://boss.yahooapis.com/ysearch/web/v1/'
        # 'http://boss.yahooapis.com/ysearch/web/v1/'+hledany_vyraz+'?appid=pELZhdHV34FgmbRCnWHvOzV1kJtKUwDGa016syd8VIW365v4jkGTpjFFHIoiCwFpOP2Y&format=xml&type=html&count=99'


    def get_yahooboss_query(self, query, count=99):
        """
        Make yahoo boss url query (URL for GET request).
        """
        url = self.ybossurl + query.replace(" ", "+") + '?' + self.ykey + self.yparams + str(count)
        return url_safe(url)


    def _del_waste_tags(self, eltree):
        """
        Delete <br> and <b></b> tags
        """
        # convert to string
        xmlcode = etree.tostring(eltree)
        # delete <b> tags
        xmlcode = xmlcode.replace('<b>', '').replace('</b>', '')
        xmlcode = xmlcode.replace(']]','').replace('??>', '?>')
        # delete DOCTYPE waste
        xmlcode = re.sub('<!DOCTYPE[^>]*>\n', '', xmlcode)
        return etree.fromstring(xmlcode) # etree.ElementTree


    def _walk(self, tree):
        """
        Parse results. Walks through element tree and stores items and their
        attributes to list.
        """
        self.xmlresult = self._del_waste_tags(tree.find("//ysearchresponse"))
        for i,result in enumerate(tree.findall('//result')):
            result = self._del_waste_tags(result) # strip useless tags
            item = {}
            for attr in result:
                item[attr.tag] = attr.text
            item['rank'] = i+1
            self.rlist.append(item)


    def parse(self, tree):
        """
        Main method.
        """
        if type(tree) != etree._ElementTree:
            raise AttributeError("parse() method requires etree._ElementTree object as tree")
        self.rlist = []
        self._walk(tree)

#-------------------------------------------------------------------------------
# end of class YahooBossParser
#-------------------------------------------------------------------------------


class AskParser(_DefaultSearchEngineParser):
    """
    Class Askparser provides API to wrapping results of Ask.com search engine.
    Main features:
        - parses inly non-sponsored results (sponsored are often useless, cause of advertisments)
        - provides methods for selecting page
        - returns URL, title, abstract and rank of result-item
    """
    def __init__(self):
        # ask.com url query
        self.askq = '?q='
        self.askparams = "&search=&qsrc=0&o=0&l=dir&page="
        self.askurl = 'http://www.ask.com/web'

        # tag sequence representing one record
        self.tagseq = ('a', 'div', 'div', 'table', 'tr', 'td', 'a')
        self.tagseq2 = ('a', 'div', 'a', 'br', 'span', 'span', 'tr')
        self.tagseq3 = ('a', 'table', 'tr', 'td', 'a', 'img', 'td', 'div', 'div')
        self.tagseq4 = ('a', 'table', 'tr', 'td', 'div', 'a', 'img', 'a', 'script', 'td', 'div', 'a')

        # xml output storage
        self.xmlresult = etree.Element("asksearchresponse")
        self.resultset = etree.SubElement(self.xmlresult, "resultset_web")
        self.totalhits = '0'


    def get_ask_query(self, query, page=1):
        """
        Main ask url query.
        """
        q = re.sub("[ ]+", "+", query)
        url = self.askurl + self.askq + q + self.askparams + str(page)
        return url_safe(url)


    def parse(self, tree, genxml=True):
        """
        Main public method for searching.
        """
        if type(tree) != etree._ElementTree:
            raise AttributeError("parse() method requires etree._ElementTree object as tree")
        self.rlist = []
        self.tree = tree
        self._walk()
        if genxml: self._genxmltree()


    def _handle_type(self, textpos):
        item = {}
        # url
        item['url'] = self.aseq[0].get('href')

        # title
        txt = self.aseq[0].text
        txt = re.sub("[ ]+", " ", txt)
        item['title'] = txt

        # abstract
        abstract = self.aseq[textpos].text
        if abstract:
            abstract = re.sub("[ ]+", " ", abstract)
            item['abstract'] = abstract
        else:
            return
        # rank
        item['rank'] = self.rankcounter
        # increase rankcounter
        self.rankcounter += 1
        # store in resultList
        self.rlist.append(item)


    def _walk(self):
        """
        Go through structure of the web and harvest data. Store result into
        self.rlist variable.
        """
        page = re.sub("(&#13;)|(\n)", "", etree.tostring(self.tree))
        page = re.sub("</?b>", "", page)
        self.aseq = []
        self.counter = 0
        self.rankcounter = 1
        self.type = None

        # -- fixed in version 0.10.6.21 --
        # there was bug in parsing non-valid html. Added etree.HTMLParser with
        # recovery param.
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO.StringIO(page), parser)

        for tag in tree.getroot().iterdescendants():
        # -- end of fixed code --
            #////////////////////////////////////////////////////////////
            # FIXME ugly if-else spaghetti code..
            # Previous state: Worked on some type of result-items, but not on every.
            # State now: God bless IF-ELSE statement. Works on every (?) item type.
            # Future state: God bless simple and smart code. Works on every (!) item type.
            if self.counter == 0:
                if tag.tag == self.tagseq[0]:
                    self.type = [self.tagseq,self.tagseq2,self.tagseq3]
            elif self.counter == 1:
                if tag.tag == self.tagseq[1]:
                    self.type = [self.tagseq,self.tagseq2]
                elif tag.tag == self.tagseq3[1]:
                    self.type = [self.tagseq3, self.tagseq4]
            elif self.counter == 2:
                if self.tagseq in self.type:
                    if tag.tag == self.tagseq[2]:
                        self.type = [self.tagseq]
                    elif tag.tag == self.tagseq2[2]:
                        self.type = [self.tagseq2]
            elif self.counter == 4:
                if self.tagseq3 in self.type:
                    if tag.tag == self.tagseq3[4]:
                        self.type = [self.tagseq3]
                    elif tag.tag == self.tagseq4[4]:
                        self.type = [self.tagseq4]
            #////////////////////////////////////////////////////////////
            if self.type == None: continue
            if tag.tag == self.type[0][self.counter]:
                self.counter += 1
                self.aseq.append(tag)
                if self.counter == (len(self.type[0])-1):
                    if self.type[0] == self.tagseq:
                        self._handle_type(1)
                    # use type 1 handler for type 2, cause it's the same format
                    elif self.type[0] == self.tagseq2:
                        # yes, handle_type1 - it is the same format!
                        self._handle_type(1)
                    elif self.type[0] == self.tagseq3:
                        self._handle_type(7)
                    elif self.type[0] == self.tagseq4:
                        self._handle_type(10)
                    # delete counters and sequences
                    self.counter = 0
                    self.aseq = []
                    self.type = None

            else:
                # delete counters and sequences
                self.counter = 0
                self.aseq = []
                self.type = None

#-------------------------------------------------------------------------------
# end of class AskParser
#-------------------------------------------------------------------------------


class BingParser(_DefaultSearchEngineParser):
    def __init__(self):

        self.tagseq = ('h3', 'a', 'p')
        self.seqlen = len(self.tagseq)

        # xml output storage
        self.xmlresult = etree.Element("bingsearchresponse")
        self.resultset = etree.SubElement(self.xmlresult, "resultset_web")

        self.bingurl = 'http://www.bing.com/search?q='
        self.bingparam = '&go=&filt=all&qs=n&sk=&first='


    def parse(self, elemtree, genxml=True):
        """
        Main public method for searching.
        """
        if type(elemtree) != etree._ElementTree:
            raise AttributeError("parse() method requires lxml.etree._ElementTree object as tree")
        self.rlist = []
        self.elemtree = self._del_waste_tags(elemtree)
        self._walk()
        if genxml: self._genxmltree()


    def _del_waste_tags(self, block):
        """
        Delete <br> and <b></b> tags
        """
        htmlcode = etree.tostring(block)
        htmlcode = re.sub('<br[^\>]*>', '', htmlcode)
        htmlcode = htmlcode.replace('<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:web="http://schemas.live.com/Web/" xml:lang="en">', '<html>')
        return lh.fromstring(htmlcode)


    def get_bing_query(self, query, page=1):
        """
        Make Bing url query (URL for GET request).
        """
        url = self.bingurl + query.replace(" ", "+") + self.bingparam + str((int(page)*10)-9)
        return url_safe(url)



    def _extract_totalhits(self, tag):
        """
        Harvests total count of hits returned by search engine to queried phrase.
        """
        total_split = (tag.text).split(" ")
        self.totalhits = total_split[2].replace(",", "")


    def _walk(self):
        """
        Go through structure of the web and harvest data. Store result into
        self.rlist variable.
        """
        self.pointer = 0
        self.rankcounter = 1
        for tag in self.elemtree.iterdescendants():
            if tag.get('id') == "results":
                self.elemtree = tag
                break
        self.rec = {}
        self.totalhits = 0
        for elem in self.elemtree.iterdescendants():
            #print tag, tag.text_content(), tag.get("id"), tag.get('class')
            tg = self.tagseq[self.pointer]
            if elem.tag == tg:
                if tg == "h3":
                    self.rec['title'] = elem.text_content()
                elif tg == "a":
                    self.rec['url'] = elem.get('href')
                elif tg == "p":
                    self.rec["abstract"] = elem.text_content()
                self.pointer += 1
                if self.pointer == 3:
                    self.pointer = 0
                    self.rec["rank"] = self.rankcounter
                    self.rlist.append(self.rec)
                    self.rec = {}
                    self.rankcounter += 1
                    
#-------------------------------------------------------------------------------
# end of class BingParser
#-------------------------------------------------------------------------------


class ClassNotImplementedException(Exception): pass

class GoogleParser:
    def __init__(self):
        raise ClassNotImplementedException("GoogleParser not implemented.")

#-------------------------------------------------------------------------------
# end of class GoogleParser
#-------------------------------------------------------------------------------

if __name__ == '__main__':
    query = "Search Engine Ranking Factors"
    crawler = Crawler()
    bing = AltaVistaParser()
    qbi = bing.get_altavista_query(query)
    res = crawler.start([qbi])
    bing.parse(res[qbi])
    for item in bing.get_list():
        print item['rank'], item['title'], item['url']
