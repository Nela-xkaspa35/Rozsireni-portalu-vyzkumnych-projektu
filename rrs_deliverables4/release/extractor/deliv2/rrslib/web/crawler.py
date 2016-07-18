#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module crawler provides methods for multi-threaded downloading, HTTP handling and
basic html repair.

Donwloading:
There are two download handlers : FileDownloader(__DefaultFileDownloader) and
GetHTMLPage(__DefaultFileDownloader). FileDownloader is a general downloader,
GetHTMLPage is specialized downloader and html parser (uses lxml library).

Threading:
Number of allowed threads is driven by MAX_THREADS constant, but default it's 30.

HTTP:
There are handled many exceptions and properties of HTTP protocol. Redirections
handled too.
"""

__modulename__ = "crawler"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$31-May-2010 11:05:34$"



import lxml.html as lh
from lxml.etree import ElementTree
import time
import urllib2
import threading
import thread
from httptools import is_url_valid
import re


# define maximal allowed amount of threads
MAX_THREADS = 30
# define timeout constant in seconds
TIMEOUT = 10

class _DefaultFileDownloader:
    """
    class DefaultFileDownloader - from this class are all downlaoders inherited.
    """

    # object init
    def __init__(self):
        self._opener = urllib2.build_opener(urllib2.HTTPRedirectHandler())
        self._opener.addheaders.append(('User-agent', 'Mozilla/5.0 (compatible; MSIE 5.5; Windows NT)'))


    def set_headers(self, hdr):
        """
        Set headers to request
        """
        self._opener.addheaders = hdr

# ------------------------------------------------------------------------------
# end of class __DefaultFileDownloader
# ------------------------------------------------------------------------------

class FileDownloader(_DefaultFileDownloader):

    def download(self, url):
        self._stream = None
        self._content = None
        # open URL
        try:
            self._stream = self._opener.open(url)
        except urllib2.URLError, err:
            return (-1, err)
        except urllib2.HTTPError, err:
            return (-1, err)
        except Exception, e:
            return (-1, e)
        self._content = self._stream.read()
        return (1, self._stream.geturl())


    def get_file(self):
        return self._content

# ------------------------------------------------------------------------------
# end of class FileDownloader
# ------------------------------------------------------------------------------

class GetHTMLPage(_DefaultFileDownloader):
    """
    class GetHTMLPage - this actually downloads the page
    """

    def get_page(self, url):
        """
        Get Html And Parse page identified by url and remember it
        """
        # delete all variables user before
        self._current_page = None
        self._current_tree = None

        # hacking altavista because it doesn't provide usefull data with
        # previous header.
        if 'altavista' in url:
            self._opener.addheaders = [('User-agent', 'Mozilla/5.0 (compatible; MSIE 5.5; Windows NT)')]


        # open URL
        try:
            self._current_page = self._opener.open(url)
        except urllib2.URLError, err:
            return (-1, err)
        except urllib2.HTTPError, err:
            return (-1, err)
        except Exception, e:
            return (-1, e)

        # parse page
        if 1:
        #try:
            #self._current_tree = lh.parse(self._current_page)
            html = self._current_page.read()
            encoding=self._current_page.headers['content-type'].split('charset=')[-1]
            if encoding  == 'text/html':
                try:
                    meta = re.search("content=[\"\']text/html; charset=[^\'\"]+[\"\']", html, re.I).group(0)
                    chs = meta.split("charset=")
                    encoding = chs[1][:-1]
                except AttributeError:
                    encoding = 'utf-8'
            try:
                uhtml = unicode(html, encoding)
            except:
                pass
            try:
                self._current_tree = ElementTree( lh.document_fromstring(uhtml) )
            except (UnboundLocalError,ValueError):
                self._current_tree = ElementTree( lh.document_fromstring(html) )
        #except Exception, e:
        #    return (-1, e)

        # final check
        # try to manipulate with element tree - if not valid, returns -1
        try:
            anch = self._current_tree.findall('//a')
        except AssertionError, err:
            return (-1, 'Broken HTML tree.')

        # successful return
        return (1, self._current_page.geturl())


    def get_etree(self):
        """
        Return element tree of last downloaded page
        """
        if self._current_tree != None:
            return self._current_tree
        else:
            return -1

    def __str__(self):
        try:
            return "<"+__modulename__+".GetHTMLPage instance at "+str(self._current_page.geturl())+">"
        except:
            return "<"+__modulename__+".GetHTMLPage instance at no URL>"

# ------------------------------------------------------------------------------
# end of class GetHTMLPage
# ------------------------------------------------------------------------------

class CrawlerThreadError(Exception):
    """
    Raised when CrawlerThread recognizes an error and throws it.
    """
    def __init__(self, msg_str, url):
        self.msg = msg_str
        self.url = url

    def __str__(self):
        return 'CrawlerThreadError occured in %s. Reason: %s' % (self.url, self.msg)


# ------------------------------------------------------------------------------
# end of class CrawlerThreadError(Exception)
# ------------------------------------------------------------------------------



class CrawlerThread(threading.Thread):
    """
    Crawler thread class. This represents one thread in processing.
    """
    def __init__(self, url, handler=GetHTMLPage, headers=None):
        # invoke constructor of parent class
        threading.Thread.__init__(self)
        # add instance variables
        if type(url) != str or not is_url_valid(url):
            raise CrawlerThreadError('Malformated URL', url)
        self.url = url
        self.handler = handler()
        if headers is not None:
            self.handler.set_headers(headers)
        self.result = None


    # set result
    def __setresult(self, result):
        """
        Stores result in the object variable.
        """
        self.result = result


    def __getresult__(self):
        """
        Returns element tree of processed page. If result isnt available,
        returns False. If an error occurs while downloading the page, returns
        tuple (code, exception).
        """
        return self.result or False


    def __geturl__(self):
        """
        Returns the real url from where the page was downloaded.
        Mainly used for redirections.
        """
        return self.url


    def run(self):
        """
        Main method fired by start() method. Handles downloading and stores
        result in object variable $result, which can taken by __getresult__()
        method.
        """
        if self.url is None:
            return
        if isinstance(self.handler, GetHTMLPage):
            ph_result = self.handler.get_page(self.url)
            if ph_result[0] == 1:
                self.__setresult(self.handler.get_etree())
                self.url = ph_result[1]
            else:
                self.__setresult(ph_result)
        elif isinstance(self.handler, FileDownloader):
            ph_result = self.handler.download(self.url)
            if ph_result[0] == 1:
                self.__setresult(self.handler.get_file())
                self.url = ph_result[1]
            else:
                self.__setresult(ph_result)
        else:
            raise CrawlerThreadError('Bad downloader type: '+self.handler.__class__, self.url)

# ------------------------------------------------------------------------------
# end of class CrawlerThread
# ------------------------------------------------------------------------------


class Crawler:
    """
    Main crawler class. Instance of this class will handle the downloading.
    """
    def __init__(self):
        self.mythreads = [] # list of all the threads
        self.queue = {}
        self.redir = {}
        self.preffered_handler = GetHTMLPage
        self._headers = None



    def __getresult(self):
        """
        Get result and delete queue.
        """
        return self.queue


    def get_redirections(self):
        """
        Returns redirected urls mapped to old urls. For example:
        {'http://www.google.com' : 'http://www.google.cz'}
        """
        return self.redir


    def set_handler(self, handler):
        """
        Set preferred download handler for downloading the queue.
        """
        self.preffered_handler = handler


    def set_headers(self, header):
        self._headers = header


    def start(self, urls):
        """
        Starts all threads. This supposed to be a main method.
        """
        self.redir.clear()
        self.queue.clear()
        if len(urls) == 0:
            return {}
        for link in urls:
            if link == None: continue
            try:
                thrd = CrawlerThread(link, self.preffered_handler, headers=self._headers)
            except CrawlerThreadError, e:
                self.queue[link] = (-1, str(e))
                continue
            # keep a list all threads
            self.mythreads.append(thrd)
            thrd.name = link

            while 1:
                # reduce max threads to MAX_THREADS
                if threading.activeCount() > MAX_THREADS:
                    time.sleep(1)
                    continue
                try:
                    thrd.start()
                    break
                except thread.error:
                    # wait for end of some thread
                    time.sleep(1)

        # wait for all threads to finish
        for s in self.mythreads:
            s.join()
            self.queue[s.name]= s.__getresult__()
            if s.name != s.__geturl__():
                self.redir[s.name] = s.__geturl__()

        mtlen = len(self.mythreads)
        for t in range(mtlen):
            self.mythreads.pop()

        return self.__getresult()


# ------------------------------------------------------------------------------
# end of class Crawler
# ------------------------------------------------------------------------------
