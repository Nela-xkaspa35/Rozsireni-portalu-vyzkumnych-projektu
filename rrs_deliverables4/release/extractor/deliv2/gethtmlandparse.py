#!/usr/bin/env python

import lxml.html as lh # have to be installed!
import sys, re, httplib, os, string
from urlparse import urlsplit
from urlparse import urlparse
from rrslib.web.crawler import GetHTMLPage
from rrslib.web.mime import MIMEHandler
import socket
import urllib2

# socket module settings
socket.setdefaulttimeout(15)


class GetHTMLAndParse:

    # init like init
    def __init__(self):
        self.crawler = GetHTMLPage()
        self.crawler.set_headers((
                   ('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.19) Gecko/2010040116 Ubuntu/9.04 (jaunty) Firefox/3.0.19'), \
                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                 ))
        self.mime_handler = MIMEHandler()

        # define wanted/unwanted file types
        self.wanted_mimes = ['application/pdf','application/msword', 'text/rtf'
                           'application/postscript', 'octet/stream',
                           'application/vnd.oasis.opendocument.text']
        self.unwanted_mimes = ['application/zip','application/x-tar',
                             'application/x-gtar']

    
    """ Get Html And Parse page identified by url and remember it """
    def ghap(self, url):
        self._current_tree = None
        ############
        # open URL #
        try:
            _res = self.crawler.get_page(url)
            if _res[0] == -1:
                self._current_tree = -1
                return (-1,_res[1])

            else:
                self._current_tree = self.crawler.get_etree()
        except:
            return (-1, 'Downloading page interrupted.')
        # successful return        
        return (1, 'OK')

    def is_wanted_mime(self,link):
        "Test if mime type of link is in wanted types for deliverables documents"

        res = self.get_content_type(link)

        if not res:
            return False

        if res in self.wanted_mimes:
           return True
        else:
           return False

    def is_unwanted_mime(self,link):
        res = self.get_content_type(link)

        if not res:
            return True

        if res in self.unwanted_mimes:
           return True
        else:
           return False

    def is_page(self,link):
        res = self.get_content_type(link)

        if res == "text/html":
            return True
        else:
            return False

    
    """ Returns MIME type of content """
    def get_content_type(self, url=None):
        # returns MIME type of current page in GHAP if parameter url is None
        if url == None:
            return False
        res = self.mime_handler.start([url])
     

        if res == None:
            print "Chyba pri zistovani mime"
            return False
        else:
            return res[url]



        """ Compare two domain names from their URLs"""
    def compare_domains(self, right, left):
        rsplit = urlsplit(right)
        lsplit = urlsplit(left)
        # now we have two tuples of parsed URLs
        if re.match("(wiki\.|www\.)?" + rsplit[1], lsplit[1], re.I):
            return 1
        else:
            return 0


    """ Simple get domain name from URL """
    def get_domain_name(self, url):
        try: # use urlsplit function
            return urlsplit(url)[1]
        except:
            return None


    """ get, filter, edit anchors and return URLs
    if parameter regul is not None, returns URLs only from anchors that
        matches for REGEXP in regul
    if parameter base is not None, makes absolute URLs as mixure of base
        and link from anchor's href atribute """
    def get_all_links(self, regul=None, base=None):
        # get all anchors
        links = self._current_tree.findall('.//a[@href]')
        final = []
        for link in links:
            # all atributes and text together
            try:
                texts = link.text_content() + " " + " ".join(link.values())
            except:
                return list()
            # make links absolute
            if base is not None:
                link.make_links_absolute(base)
            # search in links
            if regul is not None:
                if regul.search(texts): # regul matches
                    final.append(link.get('href')) # get URL
            else:
                final.append(link.get('href'))
        return list(set(final)) # my little uniq


    """ Helper method for searching pagers """
    def get_pager_links(self, base=None):
        # get all anchors with href attribute
        links = self._current_tree.findall('.//a[@href]')
        final = []
        for link in links:
            text = lh.tostring(link, method='text', encoding=unicode)
            if base is not None:
                # make links absolute
                link.make_links_absolute(base)
            # search pager pattern
            if re.search('(^ ?[0-9]+ ?$)|(next)', text, re.I):
                final.append(link.get('href')) # get URL
        return list(set(final)) # my little uniq


    """ Get, filter and count header titles on one page """
    def count_all_headers(self, regul=None):
        # look for only first 3 levels of headers
        try:
            heads = self._current_tree.findall('//h1')
            heads.extend(self._current_tree.findall('//h2')) 
            heads.extend(self._current_tree.findall('//h3'))
        except AssertionError:
            return 0
        final = []
        # search in headers
        if regul is not None:
            for head in heads:
                try: 
                    if regul.search(head.text_content()): # regul matches
                        final.append(head.text_content()) # get URL
                except UnicodeDecodeError, err:
                    return (-1, 'Unicode decode error.')
        else:
            return len(set(heads)) # count of all headers
        return len(set(final)) # count of matched headers


    """ Checks if some frames exists 
     returns list of URLs to frame pages if there are frames
     returns empty list if there are frames but no URL in src atribute
     returns None if there is not a frame """
    def look_for_frame(self, base=None):
        # get all frames on the page
        try:
            frames = self._current_tree.findall('//frameset/frame')
            frames.extend(self._current_tree.findall('//iframe'))
        except:
            return None
        # nothing found, it is noframe page
        if not frames:
            return None
        # frames found, get URLs from them
        links = []
        for frame in frames:
            # make frame URLs absolute
            if base is not None:
                basesplit = urlsplit(base)
                if re.match("/[^.]*[^/]$", basesplit[2], re.I):
                    base = base + "/"
                frame.make_links_absolute(base)
            # URL is in src attribute
            links.append(frame.get('src'))
        return links # list of frames URLs


    """ Parse anchor and get URL from href atribute
    if no href atribute exists, returns None """
    def get_link_from_anchor(self, anchor):
        anchor_element = lh.fromstring(anchor)
        return anchor_element.get('href')
 
    
    """ Check all anchors on the page and return those with link in href """
    def get_anchor_from_link(self, link):
        # get all anchors
        anchors = self._current_tree.findall('//a')
        regul = link + "(#.*)?" # REGEXP
        for anchor in anchors:
            anchor.make_links_absolute(link)
            href = anchor.get('href')
            # some anchors have not got href attribute
            if not href:
                continue
            if not re.match(regul, href, re.I):
                continue
            # we found first, return it
            try:
                return str( anchor.text ) + " " + str( anchor.get('title') )
            except:
                return 0
        return 0


    """ Get file name
    returns name of file parsed from url
    dots are translated to underscores, suffix is omitted """
    def get_file_name(self, url):
        filename = os.path.basename(url)
        if filename == '':
            filename = (urlsplit(url).path).split('/')[-1]
        elif filename == 'view':
            filename = (urlsplit(url).path).split('/')[-2]
        if filename:
            # link is with GET parameters, ask server for file name
            if re.search("\?", filename):
                spliturl = urlsplit(url)
                conn = httplib.HTTPConnection(spliturl[1])
                conn.request("HEAD", "/" + spliturl[2] + "?" + spliturl[3])
                resp = conn.getresponse()
                headers = resp.getheaders()
                for head in headers:
                    if head[0] == 'content-disposition':
                        fn = re.search("(?<=filename\=\")[^\"]+(?=\")", head[1])
                        if fn: return fn.group(0)
            return filename
        else:
            return None

    """ Returns current ElementTree from GHAP memory """
    def get_etree(self):
        # check if exists
        if not self._current_tree:
            return -1
        return self._current_tree

   
    """ Get encoding of the page.
    Return string with encoding or None if not recognized """
    def get_charset(self):
        charset = None
        meta = self._current_tree.findall('.//meta[@content]')
        for tag in meta:
            if 'charset' in tag.get("content"):
                chs = re.search("(?<=charset=)[a-zA-Z0-9\-]+$", \
                                    tag.get("content"), re.I)
                if chs:
                    charset = chs.group(0)
                break
        if charset == "windows-1250":
            charset = "cp1250"
        return charset
        
        
    """ Get keywords and description of page if reachable """
    def getkw(self):
        _meta = {}
        # look for all meta tags on the page
        metatags = self._current_tree.findall('.//meta[@content]')
        for tag in metatags:
            # check name attribute
            val = tag.get("name")
            if val == 'description':
                _meta[val] = tag.get("content")
            elif val == 'keywords':
                kwlist = tag.get("content").split(',')
                _meta[val] = map(lambda x: x.lstrip(' ').rstrip(' '), kwlist)
        return _meta


    """ Get list of anchor elements leading to deliverable documents """
    def find_anchor_elem(self, base=None, tree=None):
        delivlist = []
        # get all anchors with href attribute
        if tree == None:            
            links = self._current_tree.findall('.//a[@href]')
        else:
            links = tree.findall('.//a[@href]')
        # filter links
        for linkelem in links:
            link = linkelem.get('href')
            if 'mailto' in link: # if mail in href, skip
                continue
            if not base == None:
                if not re.match("^.*/.*", base):
                    base = base + "/"
                if link[0] == "/":
                    linkelem.set('href', link[1:])
                try:
                    linkelem.make_links_absolute(base) # make url absolute
                except:
                    pass
            link = linkelem.get('href')
            if not re.match("^http://", link):
                link = "http://" + link
            if self.is_wanted_mime(link):
                if not linkelem in delivlist:
                    delivlist.append(linkelem)
        # in delivlist we have all anchor elements carying href-atribute
        return delivlist


# end of class GetHTMLAndParse. 
