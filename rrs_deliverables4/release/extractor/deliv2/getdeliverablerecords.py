#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, re, string, textwrap
import lxml, unicodedata, htmlentitydefs
from gethtmlandparse import GetHTMLAndParse
import deliverrno as derrno
from collections import deque
from delivdbglib import DeliverableDebugger
from rrslib.xml.xmlconverter import Model2XMLConverter
from rrslib.db.model import RRSPublication,RRSUrl,RRSRelationshipPublicationUrl,RRSPublication_type,RRSRelationshipPublicationPublication_type

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


class GetDeliverableRegion:

    def __init__(self):
        # init agent for parsing html
        self.htmlHandler = GetHTMLAndParse()
        
        # format text
        self.formatter = TextFormatUtils()

    
    """ Get data region. 
    Returns element tree with region where are deliverables stored """
    def get_region(self, url, base, tolerance):
        (gresult, errmsg) = self.htmlHandler.ghap(url)
        if gresult == -1:
            return derrno.__err__(errmsg)
        
        # initialize charset to encode the page
        self.formatter.set_charset(self.htmlHandler.get_charset())
        # get anchors carying link to deliverable <a href="./deliverable.pdf">
        deliv_elements = self.htmlHandler.find_anchor_elem(base=base)
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


# get records and return dict or list of records with atributes
class GetDeliverableRecords:

    def __init__(self, verbose=False,debug=False):
        # init agent for parsing html
        self.htmlHandler = GetHTMLAndParse()        
        # to get region where to search for records
        self.regionHandler = GetDeliverableRegion()        
        # init text formatter (encoding, erasing white chars etc.)
        self.formatter = TextFormatUtils()               
        # list of acceptable words in title (header) of table
        self.table_sem_words = ['deliverable', 'description', 'name', 'date',
                                'dissemination', 'no.', 'wp', 'delivery',
                                'particip', 'title', 'nature']
        self._omitted_tags = ('br', 'img', 'html', 'body')
        # tag tolerance
        self.tagtol = 1
        # verbose and debug flags
        self.debugger = DeliverableDebugger(verbose = verbose,debug = debug)
        self.__verbose = self.debugger.verbose
        self.__debug = self.debugger.debug


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


    """ Get table order (table semantic) """
    def _get_table_order(self):
        sem_list = []
        for desc in self.parentetree.iterdescendants():
            if desc.tag == 'tr': # first <tr> match
                for col in desc: # its <th> or <td>
                    for child in col.iterdescendants():
                        if child.tag == 'a':
                             if self.htmlHandler.check_file(child.get('href')):
                                 return None
                    value = self._get_descendats_texts(col)
                    if value != None:
                        # if it is not title, but some text.
                        if len(value) > 30: 
                            return None
                        sem_list.append(value)
                break
        str_sem_list = " ".join(sem_list)
        for expr in self.table_sem_words:
            # two matches ???
            if re.search(expr, str_sem_list, re.I): 
                return sem_list
        return None


    """ Get link from row of table - go through columns and the only href
    leading to deliverable is returned. """
    def _get_row_link(self, row):
        # find all anchors where parent is row
        linkanch = row.findall('.//a[@href]')
        if len(linkanch) == 0:
            return None
        for link in linkanch:
            anchor_link = link.get('href')
            if self.htmlHandler.check_file(anchor_link): # check if it is file we want
                return anchor_link
        return None


    """ Handle region as a table.
    Work with region as it's a table. Try to get table semantic (table order)
    and get all records out of it. """
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #

    def _handle_table(self):
        # get table semantic
        tbl_order = self._get_table_order()
        # if we didnt recognize table order, get records and return list
        if not tbl_order:
            self.__verbose("Table order not recognized, getting data...")
            records = []
            # tr tag is a record
            for row in self.parentetree:
                if not row.tag == 'tr':
                    continue
                row_list = []
                _thislink = self._get_row_link(row)
                if _thislink == None:
                    continue
                row_list.append(_thislink)
                for column in row:
                    text = self._get_descendats_texts(column)
                    if not text:
                        continue
                    row_list.append(text)
                records.append(row_list)
                del(row_list)
            return records     
        # else we have recognized table order, make dict of dicts out of it
        else:
            self.__verbose("Table order recognized, filling dictionary in this order.")
            # every column of the row (every atribute of the record) has it's own
            # semantic in order of table semantic
            semantic_data = dict()
            for row in self.parentetree:
                self._thislink = self._get_row_link(row)
                # if its header or non-deliverable row, omit it.
                if self._thislink == None:
                    continue
                semantic_data[self._thislink] = {}
                for index, column in enumerate(row):
                    # get column text                    
                    text = self._get_descendats_texts(column)
                    if not text:
                        continue
                    try:
                        # store it
                        semantic_data[self._thislink][tbl_order[index]] = text
                    except:
                        continue
            return semantic_data

########################  TAG SEQUENCE RECOGNIZING METHODS ####################

    """ Tag check. 
    If it is anchor with href leading to deliverable, returns True """
    def _is_deliv_anch(self, tag):
        if tag.tag == 'a':
            href = tag.get('href')
            if self.htmlHandler.check_file(href):
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
        anchlist = self.htmlHandler.find_anchor_elem(self.baseUrl, self.parentetree)
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

   ###
   #
   #
   #
   #
   #
   #
   #
   #
   #
   #
   #
    """ Get element texts only, dont look for descendants texts """
    def _get_tag_content(self, tag):
        l = []
        if tag.tag == 'a':
            href = tag.get('href')
            # if link leading to document found, add string to list
            if href is not None and self.htmlHandler.check_file(href):
                l.append(self.formatter.format(href))
            title = tag.get('title')
            # if title found in tag, add string to list
            if title:
                l.append(self.formatter.format(title))
        # if not anchor, search text in tag.text
        if tag.text:
            if re.search("[a-z0-9]", tag.text, re.I):
                l.append(self.formatter.format(tag.text))
        return l

    
    """ Harvest texts out of tags and return list of lists (record) """
    def _harvest_text(self, record_tag_list):
        self._records = []
        self._rec = []
        # loop over records and search all possible useful texts
        for rec_list in record_tag_list:
            for tag in rec_list:
                self._rec.extend(self._get_tag_content(tag))
            self._records.append(self._rec)
            self._rec = []
        return self._records


    """ Text harvesting for sequences. """
    def _handle_sequence(self):
        seq = self._get_tag_sequences()        
        return self._harvest_text(seq)
        
############################  OVERALL METHODS  ################################

    """ Get records from region according document links """
    def _manual_process_page(self, links, baseurl):
        _err = None
        recordlist = []
        self.baseUrl = baseurl
        
        for link in links:
            # find region with tolerance
            self.parentetree = self.regionHandler.get_region(link, baseurl, 1)
            if type(self.parentetree) == tuple:
                # error
                _err = self.parentetree
                continue
            
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
                
                _result = self._handle_table()
                # if we had a dictionary, continue filling it
                if len(recordlist) > 0:
                    for key in _result:
                        recordlist[key] = _result[key]
                else:
                    recordlist = _result
            # Parent tag is not table
            # call _handle_sequence
            else:
                self.__verbose("Handling sequences")
                
                _result = self._handle_sequence()
                recordlist.extend(_result)
        # no records found            
        if len(recordlist) == 0:
            if not _err == None:
                return _err
            return derrno.__err__(derrno.ENOREC)
        self.__debug("DATA RECORDS: ")
        self.__debug(recordlist)
        return recordlist # returns list of records
    

# End of class GetDeliverableRecords


class Main: # for testing only
    def __init__(self,params):
        self.argv = params

    def print_help(self):
        print("usage: deliverables url")
        print("       [-h] prints this help.")
        sys.exit(0)

    def handle_cmd(self):
        if len(self.argv) > 2:
            print("deliverables: wrong number of parameters.") # sys.stderr.write() ??
            self.print_help()
        if len(self.argv) == 1:
            print("deliverables: missing operand: url")
            self.print_help()
        if self.argv[1] == "-h": # print help
            self.print_help()
        return self.argv[1]

if __name__ == '__main__':
    
    from urlparse import urlsplit


    main = Main(sys.argv)
    url = main.handle_cmd()
    if not "http://" in url:
        print("wrong url format.")
        sys.exit(0)

    gdr = GetDeliverableRecords()
    print gdr._manual_process_page([url], urlsplit(url)[1])
    exit()
    import cProfile
    cProfile.run("print gdr.get_records([deliv], base3)")
    
    

