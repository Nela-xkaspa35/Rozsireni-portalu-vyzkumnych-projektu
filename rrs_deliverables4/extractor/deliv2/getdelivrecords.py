#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script name: GetDelivRecords
Task: script extracts information about deliverables into objects

Input:  URL link - page with deliverables
Output: parsed records XML/objects

Brno University of Technology (BUT)
Faculty of Information Technology (FIT)

Implemented by (author): Lukas Macko

rrslib has to be in path
"""

from rrslib.web.sequencewrapper import *
from rrslib.web.mime import MIMEHandler
from rrslib.web.crawler import Crawler
from rrslib.xml.xmlconverter import Model2XMLConverter
from rrslib.db.model import RRSPublication,RRSUrl,RRSRelationshipPublicationUrl,RRSPublication_type
from urlparse import urlsplit
from lxml import etree
import string, textwrap
import lxml, unicodedata, htmlentitydefs
from gethtmlandparse import GetHTMLAndParse
from collections import deque
from delivdbglib import DeliverableDebugger
import deliverrno as derrno
import sys
import re
import string as s
import StringIO


""" Decode HTML entities to text """
class HtmlEntityDecoder:

    def __init__(self):
        # pattern to recognize html entity
        self.pattern = re.compile(r'&(#?)(x?)(\w+);')
        # dictionary translating usual entities
        self.name2text = {'apos': '\'', 'nbsp': ' ', 'mdash': '-', 'ndash': '-',
                          'ldquo': '\"', 'rdquo': '\"', 'lsquo': '\'',
                          'rsquo': '\'', 'lsaquo': '<', 'rsaquo': '>'}


    """ Get the entity and return character or unicode """
    def _substitute_entity(self, match):
        entity_name = match.group(3)
        try:
            entdef = self.name2text.get(entity_name)
        except:
            entdef = htmlentitydefs.entitydefs.get(entity_name)
        return entdef


    """ Returns string with decoded entities"""
    def decode_htmlentities(self, string):
        dec_string = self.pattern.sub(self._substitute_entity, string)
        return dec_string

# End of class HtmlEntityDecoder


""" Utility for encoding and formatting text """
class TextFormatUtils:

    def __init__(self):
        # init wrapper
        self.wrapper = textwrap.TextWrapper(width=500, expand_tabs=False)

        # init entity decoder
        self.hed = HtmlEntityDecoder()

        # charset (iso-8859-2, cp1250 etc.)
        self.charset = None

    """ Charset initializer """
    def set_charset(self, chs):
        self.charset = chs

    """ Get formatter charset """
    def get_charset(self):
        return self.charset


    """ Main method formats the string:
     delete white characters (\t,\n etc),
     encode the string to utf-8 and return useful text. """
    def format(self, data):
        # endcode
        encode_flag = False
        for chset in (self.charset, 'iso-8859-2', 'cp1250', 'iso-8859-1'):
            try:
                data = data.decode(chset).encode('utf-8')
                encode_flag = True
                break
            except:
                continue
        if encode_flag:
            data = unicode(data, 'utf-8')
            data = unicodedata.normalize('NFKD', data)
        # decode html entities
        data = self.hed.decode_htmlentities(data)
        # delete white characters
        try:
            wrapped_array = self.wrapper.wrap(data)
            data = ''.join(wrapped_array)
        except:
            pass
        # delete spaces
        data = re.sub('[ ]+', ' ', data)
        return data.lstrip(' ').rstrip(' ')

# End of class TextFormatUtils

"Search region with deliverables. Only used when processing"
class GetDeliverableRegion:

    def __init__(self):
        # init agent for parsing html
        self.agent = GetHTMLAndParse()

        # format text
        self.formatter = TextFormatUtils()
        
    

    """ Get data region.
    Returns element tree with region where are deliverables stored """
    def get_region(self, url, base, tolerance):
        _res = self.agent.ghap(url)
        if len(_res) == 0:
            return derrno.__err__(errmsg)
        else:
            self._page = self.agent.get_etree()
           
        deliv_elements = self.agent.find_anchor_elem(base=base)
        if len(deliv_elements) == 0:
            return derrno.__err__(derrno.ENODOC, url)
        if len(deliv_elements) == 1:
            return lxml.etree.ElementTree(deliv_elements[0])

        # get parent tag of all deliverable anchors
        parent_element = self._get_common_parent(deliv_elements, tolerance)
        if parent_element == None:
            return derrno.__err__(derrno.ENOREG, "Parent element not found.")

        # get the region out of the parent element
        region = self._get_deliverable_region(parent_element)
        # if parent tag is region
        if region == 0:
            # return element tree made from parent tag
            return lxml.etree.ElementTree(parent_element)
        else:
            print
            #lxml.etree.ElementTree(region).write(sys.stdout,pretty_print=True)
        return region # else return region

   
    """ Stabile searching parent of all elements in elem_list
    using method of making element parent vectors and comparing them.
    Tolerance of n tags makes the region smaller if there are
    >>not deliverable<< pdfs in more regions on the page."""
    def _get_common_parent(self, elem_list, tolerance):

        # supporting method - kind of bigger lambda. Get minimal length of
        # inside lists.
        def _minlength(seq_list):
            return min([len(seq) for seq in seq_list])

        # next supporting method: check the elements in list.
        # if elements are the same, its common parent tag - return True.
        def _iscommon(elem_seq, tol):
            tol_list = []
            for elem in elem_seq:
                if not elem in tol_list:
                    tol_list.append(elem)
            if len(tol_list) > tol+1:
                return False
            # if only two anchors found then we have only two tags
            # and its pretty hard to use tolerance, so we omit it.
            if len(elem_seq) < 3 and len(tol_list) > 1:
                return False
            return True

        # get the most frequenced tag in list
        def _most_frequent(seq):
            suplist = []
            suplist_freq = []
            for el in seq:
                if not el in suplist:
                    suplist.append(el)
                    suplist_freq.append(int(1))
                else:
                    suplist_freq[suplist.index(el)] += 1
            ind = suplist_freq.index(max(suplist_freq))
            return suplist[ind]

        #
        # now continue with method _get_common_parent()
        #
        vectors = [] # here will be vectors stored - list of lists
        for self.elem in elem_list:
            _vector = []
            while 1:
                parent = self.elem.getparent() # exception possible here
                if parent == None:
                    break
                _vector.append(parent)
                self.elem = parent
            vectors.append(_vector)
        # We have parent vectors of all elements from elem_list stored in list
        # $vectors. Then zip the vector list and get sequences of parent tags (and the
        # other tags) sorted from the highest to the lowest parent element.
        zipped = [[row[-i] for row in vectors] for i in range(1, _minlength(vectors)+1)]
        # now check all lists in list zipped. If these are filled with the same
        # elements, its a common parent. The last list before difference contains
        # the main parent tag.
        self.last_seq = []
        for zipvect in zipped:
            if not _iscommon(zipvect, tolerance):
                # return most frequented element in last vector
                return _most_frequent(self.last_seq)
            self.last_seq = zipvect
        return _most_frequent(self.last_seq)


    """ Get texts from element and his descendants.
    If string is True, returns texts as one string with spaces.
    elem: lxml element """
    def _get_element_texts(self, elem, string=True):
        texts = []
        for child in elem.iter():
            if child.text and isinstance(child.tag, basestring):
                if re.search("[a-z0-9]", child.text, re.I):
                    texts.append(self.formatter.format(child.text))
        if string:
            return " ".join(texts)
        return texts


    """ Get deliverable region - returns etree with region.
     If 0 returned parent_tag is region,
     if -1 returned some error occured searching,
     if html string returned its a region. """
    def _get_deliverable_region(self, parent_tag):
        def _convert_tag_to_html(tag):
           tag_html = lxml.etree.ElementTree(tag)
           return lxml.etree.tostring(tag_html)

        # list[0] = type, list[1] = atribute, list[2] = lxml tag element
        # in case of headers list[0] = element.tag, then [2] is element
        _reg_atr = ['',None,None]
        self._result_html_region = ''
        reg_flag = False # flag indicating that we are looping over region
        # get headers first
        headers = []
        #lxml.etree.ElementTree(parent_tag).write(sys.stdout,pretty_print=True)
        for i in range(1,7):
            headers.extend(parent_tag.findall('.//h'+str(i)))
        children = parent_tag.getchildren()
        if len(headers) > 0:
            for head in headers:
                text = self._get_element_texts(head)
                if text:
                    if re.search("deliverables", text, re.I):
                        _reg_atr[0] = head.tag
                        _reg_atr[2] = head
                        break
            if _reg_atr[2] == None:
                return 0
            # visit all tag in parent_tag
            for tag in parent_tag.iterdescendants():
                if tag.tag == 'img': continue;
                text = self._get_element_texts(tag)
                if tag.tag == 'a' and not tag.text:
                    if tag.find('img') is not None:
                        text = tag.find('img').tail
                    else:
                        text = ' '
                if text:
                    if re.search("deliverables", text, re.I) and \
                        tag.tag == _reg_atr[0]:
                        # "deliverable" title, BEGIN of region
                        reg_flag = True
                    elif not re.search("deliverables", text, re.I) and \
                        tag.tag == _reg_atr[0]:
                        # next similar title, END of region
                        if reg_flag:
                           break
                # region content
                if tag in children and reg_flag:
                    self._result_html_region += _convert_tag_to_html(tag)
                elif tag.getparent() in children and reg_flag:
                    self._result_html_region+=_convert_tag_to_html(tag.getparent())
                    children.remove(tag.getparent())
        # if we dont have headers, try to find other kind of header (title)
        # "Deliverables" and compare with other elements with the same class or id.
        else:
            for tag in parent_tag.iter():
                if tag.text:
                    if re.search("deliverables", tag.text, re.I):
                        if tag.get("class"):
                            _reg_atr[0] = 'class'
                            _reg_atr[1] = tag.get("class")
                            _reg_atr[2] = tag
                            break
                        elif tag.get("id"):
                            _reg_atr[0] = 'id'
                            _reg_atr[1] = tag.get("id")
                            _reg_atr[2] = tag
                            break
                        elif tag.get("style"):
                            _reg_atr[0] = 'style'
                            _reg_atr[1] = tag.get("style")
                            _reg_atr[2] = tag
                            break

            # test _reg_atr. If there is no deliverable region, then all
            # documents make the region
            if _reg_atr[2] == None:
                return 0
            reg_flag = False
            # visit all tag in parent_tag
            for tag in parent_tag.iterdescendants():
                if tag.tag == 'a' and not tag.text:
                    if tag.find('img') is not None:
                        tag.text = tag.find('img').tail
                    else:
                        tag.text = ' '
                if tag.text:
                    if re.search("deliverables", tag.text, re.I) and \
                        tag.get(_reg_atr[0]) == _reg_atr[1]:
                        # "deliverable" title, BEGIN of region
                        reg_flag = True
                    elif not re.search("deliverables", tag.text, re.I) and \
                        tag.get(_reg_atr[0]) == _reg_atr[1]:
                        # next similar title, END of region
                        if reg_flag:
                            break
                # region content
                if tag in children and reg_flag:
                    self._result_html_region += _convert_tag_to_html(tag)
                    children.remove(tag)
                elif tag.getparent() in children and reg_flag:
                    self._result_html_region+=_convert_tag_to_html(tag.getparent())
                    children.remove(tag.getparent())
        if not self._result_html_region:
            return 0
        # create ElementTree from region
        try:
            return lxml.etree.fromstring(self._result_html_region)
        except:
            try:
                parser = lxml.etree.HTMLParser()
                return lxml.etree.fromstring(self._result_html_region, parser)
            except lxml.etree.XMLSyntaxError:
                return 0


# End of class GetDeliverableRegion

""" Class extracts records from deliv page / region"""
class GetDelivRecords:


    def __init__(self,verbose=False,debug=False):
        self.__dbg__  = debug
        self.__verbos = verbose
        self._crawler = Crawler()
        self._crawler.set_headers((
                   ('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.19) Gecko/2010040116 Ubuntu/9.04 (jaunty) Firefox/3.0.19'), \
                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                 ))
        self._wraper = HTMLSequenceWrapper(childcoef=5.0, headercoef=3.0, mintextlen=20)
             
        self._unwanted_titles = ['Download here','PDF format']
        self._records = []

        ################################
        #manual processing
        self.agent = GetHTMLAndParse()
        # to get region where to search for records
        self.regionHandler = GetDeliverableRegion()
        # init text formatter (encoding, erasing white chars etc.)
        self.formatter = TextFormatUtils()
        
        self._omitted_tags = ('br', 'img', 'html', 'body')
        # tag tolerance
        self.tagtol = 1
        

    def __debug(self, msg):
        _err = "cannot decode debug info."
        if self.__dbg__ == True:
            try:
                print("Debug message:    "+str(msg))
            except UnicodeError:
                print(_err)
    def __verbose(self,msg):
        _err = "cannot decode debug info."
        if self.__verbose == True:
            try:
                print("Verbose:    "+str(msg))
            except UnicodeError:
                print(_err)

    
    
########################Processing sequencewrapper output######################
    """function gets an entry from output of sequence wrapper
       it tries to create deliv record and retruns true if succed. """
    def _make_deliv_record(self,entry):
        
        text  = []
        links = []

        #harvest links and text form entry
        for e in entry.iter():
            if e.text != None:
                text.append(e.text)
            if e.attrib.get("link")!=None:
                if self.agent.is_wanted_mime(e.attrib.get("link")) and e.attrib.get("link") not in links:
                   links.append(e.attrib.get("link"))


        res = self._deliv_in_text(text,links)
        if type(res) == RRSPublication:
            self._entriesFoundInText.append(res)
            self.__debug("Record found cause of text")
            return True

        elif type(res)==list:
            res=self._more_entry_in_record(entry)
            if(res==True):
               self.__debug("")
               return True
            else:
               return False

        res = self._deliv_in_link(text,links,entry)
        if type(res) == RRSPublication:
            self._entriesFoundInLinks.append(res)
            self.__debug("Record found cause of link")
            return True

        return False

    """look for keyword in text"""
    def _deliv_in_text(self,text,links):
        
        #print text
        #print links
        #print "*"*40
        _title = False
        _description = ""
        pattern = re.compile("(DELIVERABLES?)|(D[0-9][0-9]*(.[0-9][0-9]*)?)",re.I)

        #loop through text in entry looking for title and description
        for t in text:
           if _title == False:
              if pattern.search(t):
                     _title = t


           #set the longest string as description of deliverable
           if len(_description)<len(t):
                _description = t

        if _title == _description:
            _description = ""

        _link = False

        if type(links) == str:
            if self.agent.is_wanted_mime(links):
                _link = links
        elif type(links) ==list:
            for l in links:
                if self.agent.is_wanted_mime(l):
                    if _link == False:
                       _link = l
                    else:
                       #if there was already found link
                       if _link[:s.rfind(_link,'.')] == l[:s.rfind(l,'.')]:
                          break
                       else:
                          return ['-3','Probably more records in one entry']

        
        #create object
        if _title:
            #print "TITLE:"+_title
            pub = RRSPublication(title=_title,abstract=_description)
            _typ = RRSPublication_type(type='techreport')
            pub['type'] = _typ
            self.__debug("*"*40)
            self.__debug("Title: "+_title)
            self.__debug("Description: "+_description)



            if _link:
                #print "LINK:"+_link
                self.__debug("Link: "+_link)
                l = RRSUrl(link=_link)
                pl_rel = RRSRelationshipPublicationUrl()
                pl_rel.set_entity(l)
                pub['url'] = pl_rel

            return pub
        else:
            #this entry is not probably deliverable
            return False

    """look for a key word in link"""
    def _deliv_in_link(self,text,links,entry = False):
        
        ##print text
        ##print links
        #print "*"*40
        
        _title = False
        _description = ""
        pattern = re.compile("(DELIVERABLES?)|(D[0-9][0-9]*(.[0-9][0-9]*)?)",re.I)

        _link = False
        
        for l in links:
            if pattern.search(l):
                  if _link == False:
                     _link =l
                  else:
                     return ['-3','Probably more records in one entry']



        #loop through text in entry looking for title and description
        for t in text:
           if _title == False:
                if len(t)>10 :
                     _title = t
           #set the longest string as description of deliverable
           if len(_description)<len(t):
                _description = t
             

        if _title == _description:
            _description = ""

        #if chosen title is not valid try to find better in parent entry
        if _title and not self._check_title(_title) and entry != False:
            _title = self._repair_title(entry)        
       
        
        #create object
        if _link:
            pub = RRSPublication(title=_title,abstract=_description)
            typ = RRSPublication_type(type='techreport')
            pub['type'] = typ

            self.__debug("*"*40)
            self.__debug("Title: "+_title)
            self.__debug("Description: "+_description)
            
            self.__debug("Link: "+_link)
            l = RRSUrl(link=_link)
            pl_rel = RRSRelationshipPublicationUrl()
            pl_rel.set_entity(l)
            pub['url'] = pl_rel
            
            return pub
        else:
            #this entry is not probably deliverable
            return False

    """Check if title contents only unwanted string with some tolerance
    return true if title is ok
    """
    def _check_title(self,title,tolerance=10):
        
        for t in self._unwanted_titles:
           if (s.find(s.lower(title),s.lower(t))) != -1:
               if (len(t)+tolerance) > len(title):
                   return False
        return True

    "looks for an element with highest visibility rank in parent elemet"
    def _repair_title(self,entry):
        parent = entry.getparent()
        visibility = 0
        title = ""
        for i in parent.iter():
             try:
                 if i.attrib.get('visibility') > visibility:
                     visibility = i.attrib.get('visibility')
                     title = i.text
             except AttributeError:
                 pass

        if title != "":
            return title
        else:
            return False

    "Function try to create array of deliverables from one entry in xml tree"
    def _more_entry_in_record(self,entry):
        for ch in entry.iter('chunk'):
           if ch.text != None and ch.attrib.get("link")!=None:
              if self.agent.is_wanted_mime(ch.attrib.get("link")):
                 _pub= RRSPublication(title=ch.text)
                 typ = RRSPublication_type(type='techreport')
                 _pub['type'] = typ
                 _l = RRSUrl(link=ch.attrib.get("link"))
                 _rel = RRSRelationshipPublicationUrl()
                 _rel.set_entity(_l)
                 _pub['url'] = _rel
                 self._entriesFoundInLinks.append(_pub) 
      
    "Process pages definied by urls"
    def process_pages(self,pages):
       self._entriesFoundInText = []
       self._entriesFoundInLinks = []
       self._urls = pages
       self._pages = self._crawler.start(pages)
       

       #creates RRSPublication objects with information about deliverables
       for u in self._urls:
          self._wraper.wrap(self._pages[u],u)
          self._tree = self._wraper.get_etree()
          #print self._wraper.get_xml()
          for entry in self._tree.iter("entry"):
             self._make_deliv_record(entry)
          
       
       if len(self._entriesFoundInText)>3:
            self.__debug("Deliverbles descriptions content keywords")
            self.__debug("Found " + "{0}".format(len(self._entriesFoundInText)) + " deliv records")
       
            self._records = self._entriesFoundInText
       elif len(self._entriesFoundInLinks)>3:
            self.__debug("Deliverbles links content keywords")
            self.__debug("Found " + "{0}".format(len(self._entriesFoundInLinks)) + " deliv records")
       
            self._records = self._entriesFoundInLinks
       else:
            self._manual_processing()
            

    "This method is called when ther was no records found in output of sequencewrapper"
    def _manual_processing(self):
        self._entriesFoundInLinks = []
        self._entriesFoundInText = []
        self._manual_process_page(self._urls, urlsplit(self._urls[0])[1])
        if len(self._entriesFoundInText)>0:
            self.__debug("Deliverbles descriptions content keywords")
            self.__debug("Found " + "{0}".format(len(self._entriesFoundInText)) + " deliv records")

            self._records = self._entriesFoundInText
        elif len(self._entriesFoundInLinks)>0:
            self.__debug("Deliverbles links content keywords")
            self.__debug("Found " + "{0}".format(len(self._entriesFoundInLinks)) + " deliv records")

            self._records = self._entriesFoundInLinks

    ########################### TABLE HANDLING METHODS ############################

    """ Get texts from element and his descendants.
    If string isset, returns texts as one string with spaces.
    # elem: lxml element """
    def _get_descendats_texts(self, elem, string=True):
        texts = []
        for child in elem.iter():
            if child.text and isinstance(child.tag, basestring):
                if re.search("[a-z0-9]", child.text, re.I):
                    texts.append(self.formatter.format(child.text))
        if string:
            return " ".join(texts)
        return texts


  
    """ Get link from row of table - go through columns and the only href
    leading to deliverable is returned. """
    def _get_row_link(self, row):
        # find all anchors where parent is row
        linkanch = row.findall('.//a[@href]')
        if len(linkanch) == 0:
            return None
        for link in linkanch:
            anchor_link = link.get('href')
            if self.agent.is_wanted_mime(anchor_link): # check if it is file we want
                return anchor_link
        return None


    """ Handle region as a table.
    Work with region as it's a table. Try to get table semantic (table order)
    and get all records out of it. """
    def _handle_table(self):
        for row in self.parentetree:
            if not row.tag == 'tr':
                continue
            row_list = []
            _thislink = self._get_row_link(row)
            if _thislink == None:
                continue

            for column in row:
                text = self._get_descendats_texts(column)
                if not text:
                    continue
                row_list.append(text)

            res = self._deliv_in_text(row_list, [_thislink])
            if type(res) == RRSPublication:
                self._entriesFoundInText.append(res)
                self.__debug("Record found cause of text")
            else:
                res = self._deliv_in_link(row_list, [_thislink])
                if type(res) == RRSPublication:
                    self._entriesFoundInLinks.append(res)
                    self.__debug("Record found cause of link")
            del(row_list)
        return 
       

########################  TAG SEQUENCE RECOGNIZING METHODS ####################

    """ Tag check.
    If it is anchor with href leading to deliverable, returns True """
    def _is_deliv_anch(self, tag):
        if tag.tag == 'a':
            href = tag.get('href')
            if self.agent.is_wanted_mime(href):
                return True
        return False


    """ Filters useless and messy tags.
    Return false if useless, true if normal tag """
    def _tagfilter(self, tag):
        if tag.tag in self._omitted_tags:
            return False
        #if tag.text:
        #    if not re.search("[a-z0-9\[\]]", tag.text, re.I):
        #        return False
        return True


    """ Gets difference between first two anchors. """
    def _getdiff(self, reg, tol):
        # etree reg = element tree region
        # int tol: accepted tolerance of tags
        d = {}
        index = 0
        # fill the dictionary with differences and their occurences
        for tag in reg.iter():
            if not self._tagfilter(tag):
                continue
            if self._is_deliv_anch(tag) and not index == 0:
                try:
                    d[index] += 1
                except:
                    d[index] = 1
                index = 0
            index += 1
        # check differencies if the variety isn't higher then $tol tolerance
        difflist = d.keys()
        self.__debug("difflist: "+str(difflist))
        if len(difflist) == 0:
            return -1
        _max = max(difflist)
        _min = min(difflist)
        dlen = len(d.keys())
        if dlen == 1:
            return d.keys()[0]
        if dlen > ((2*tol)+1): # tolerance to both sides
            return -1
        if (_max - _min) > 2*tol: # some acceptable tolerance
            return -1
        # get the most frequent difference
        most_freq = max(d.values())
        for key in d:
            if d[key] == most_freq:
                return key
        return -1


    """ Only anchors found. No optional information. """
    def _get_anch_only(self):
        anchlist = self.agent.find_anchor_elem(self.baseUrl, self.parentetree)
        # We have to make list of list because XMLOutput
        return [[anch] for anch in anchlist]

    
    """ Main method handling tag sequences and recognizing records.
    Returns list of records. """
    def _get_tag_sequences(self, tag_tol=1):
        records = []
        self._rec = []
        if len(self.parentetree) == 0:
            return [[self.parentetree]]
        # get interval between anchors, use tolerance tag_tol
        self.difference = self._getdiff(self.parentetree, self.tagtol)
        while self.difference == -1:
            if self.tagtol > 5:
                self.__verbose("Variety of intervals between anchors is too huge. "+\
                               "Getting data out of anchors only")
                return self._get_anch_only()
            self.tagtol += 1
            self.difference = self._getdiff(self.parentetree, self.tagtol)

        # get sequence of first n tags, where n is average interval between anchors
        # this could be tag-sequence describing all records in region.
        self.record_seq = []
        i = 0
        for tag in self.parentetree.iter():
            if not self._tagfilter(tag):
                continue
            if i >= self.difference:
                if not 'a' in self.record_seq:
                    del self.record_seq[0]
                else:
                    break
            self.record_seq.append(tag.tag)
            i += 1

        # counter indicates on which position in tag sequence we actually are
        counter = 0
        # make sequence of tags as they go
        regionlist = filter(self._tagfilter, [tag for tag in self.parentetree.iter()])
        recseqlen = len(self.record_seq)
        reglistlen = len(regionlist)

        # flag indicating begin of records - in region on the beginning can be some garbage
        self.begin = False
        # indicating unpredictable separator between deliverable records
        self.separator = 0
        for i, tag in enumerate(regionlist):
            # skip and save the sequence at the end
            if counter > self.difference-1:
                records.append(self._rec) # save
                self._rec = [] # erase the list
                counter = 0 # reset counter
            if not self.begin:
                if tag.tag != self.record_seq[0]:
                    continue
                else:
                    try:
                        if regionlist[i+1].tag != self.record_seq[1]:
                            continue
                    except:
                        pass
                    self.begin = True
            # handle tolerances, try to compare sibling tags
            self.match = False # match flag

            # tolerance algorithm. Goes through html and tries to pass irregular tags in sequence.
            for tol in range(self.tagtol+1):
                if tag.tag == self.record_seq[(counter + tol) % recseqlen] or \
                   regionlist[(i + tol) % reglistlen].tag == self.record_seq[counter % recseqlen]:
                    self.match = True
                    self._rec.append(tag)
                    counter += tol+1
                    break
                elif tag.tag == self.record_seq[(counter - tol) % recseqlen] or \
                   regionlist[(i - tol) % reglistlen].tag == self.record_seq[counter % recseqlen]:
                    self.match = True
                    self._rec.append(tag)
                    counter -= tol
                    counter += 1
                    break
            # if nothing matched, its probably out of tolerance
            if not self.match:
                self.separator += 1
                # tolerance 10 separators (tags between boxes or tables of deliverables)
                if self.separator > 10:
                    self.__verbose("Tag sequence doesnt match, probably out of "+\
                                "tolerance, getting data out of anchors only")
                    # maybe here could be tolerance++
                    # we didnt catch the sequence with tolerance...
                    return self._get_anch_only()
        records.append(self._rec)
        return filter(self._validseq, records)


    """ Helper method - check if sequence of tags rec contains deliv anchor
    """
    def _validseq(self, rec):
        for _atr in rec:
            # if we have anchor containing link to document, return true
            if self._is_deliv_anch(_atr):
                return True
        return False

  
    """ Get element texts only, dont look for descendants texts """
    def _get_tag_content(self, tag):
        links = []
        texts = []
        if tag.tag == 'a':
            href = tag.get('href')
            # if link leading to document found, add string to list
            if href is not None and self.agent.is_wanted_mime(href):
                links.append(self.formatter.format(href))
            title = tag.get('title')
            # if title found in tag, add string to list
            if title:
                texts.append(self.formatter.format(title))
        # if not anchor, search text in tag.text
        if tag.text:
            if re.search("[a-z0-9]", tag.text, re.I):
                texts.append(self.formatter.format(tag.text))
        return [links,texts]


    """ Harvest texts out of tags and return list of lists (record) """
    def _harvest_text(self, record_tag_list):
        self._records = []
        self._rec = []
        _links = []
        _texts = []
        # loop over records and search all possible useful texts
        for rec_list in record_tag_list:
            for tag in rec_list:
                harvested = (self._get_tag_content(tag))
                _links.extend(harvested[0])
                _texts.extend(harvested[1])
            #self._records.append(self._rec)
            res = self._deliv_in_text(_texts, _links)
            if type(res) == RRSPublication:
                 self._entriesFoundInText.append(res)
                 self.__debug("Record found cause of text")
            else:
                 res = self._deliv_in_link(_texts, _links)
                 if type(res) == RRSPublication:
                      self._entriesFoundInLinks.append(res)
                      self.__debug("Record found cause of link")
            _links = []
            _texts = []
            self._rec = []
        return self._records


    """ Text harvesting for sequences. """
    def _handle_sequence(self):
        seq = self._get_tag_sequences()
        return self._harvest_text(seq)



    """ Get records from region according document links
        this method is used when there was no records found
        in output of sequencewrapper"""
    def _manual_process_page(self, links, baseurl):
        _err = None
        self.baseUrl = baseurl

        for link in links:
            # find region with tolerance
            self.parentetree = self.regionHandler.get_region(link, baseurl, 1)
            if type(self.parentetree) == tuple:
                # error
                _err = self.parentetree
                self.__debug(_err)
                continue
            #make all links absolute in parent tree
            hrefs = self.parentetree.findall('.//a[@href]')
            for href in hrefs:
                href.make_links_absolute('http://'+urlsplit(link)[1]+'/')
            
            # get the charset. We dont have etree in htmlHandler,
            # so we have to use the one from regionHandler
            self.formatter.set_charset(self.regionHandler.formatter.get_charset())

            self.__debug("*"*100+'\n'+"*"*40+" DATA REGION "+"*"*40)
            self.__debug(lxml.etree.tostring(self.parentetree, pretty_print=True))
            # get root tag
            try:
                self.parentetree = self.parentetree.getroot()
            except:
                pass
            
            # Parent tag is table
            # call _handle_table
            if self.parentetree.tag in ('table','tbody'):
                self.__verbose("Handling table")
                self._handle_table()
            else:
                self.__verbose("Handling sequences")
                self._handle_sequence()
    

#############PUBLIC METHODS TO GET RESULTS
    def get_deliverables_XML(self):
        """return infromations about deliverables stored in objects as xml"""
        if len(self.get_deliverables())==0:
            return derrno.__err__(derrno.ENOREC)
        output = StringIO.StringIO()
        converter = Model2XMLConverter(stream=output)
        converter.convert(self.get_deliverables())
        result = output.getvalue()
        output.close()
        return result
        

    def get_deliverables(self):
        """return objects containing infromations"""
        if len(self._records) == 0:
            return derrno.__err__(derrno.ENOREC)
        else:
            return self._records



###Only for testing
if __name__ == "__main__":
  
    url = ['http://www.asisknown.org/index.php?id=32']

    if len(sys.argv)== 2:
        url=[sys.argv[1]]
    else:
        print "Usage: "+sys.argv[0]+" url"
        print "e.g: http://www.asisknown.org/index.php?id=32"
        exit() 
  
    gdr = GetDelivRecords(debug=True)
    gdr.process_pages(url)
    print gdr.get_deliverables_XML()
    