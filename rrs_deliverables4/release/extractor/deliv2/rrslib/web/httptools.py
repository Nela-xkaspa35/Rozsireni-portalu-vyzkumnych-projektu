#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
rrslib.web.httptools is mixed-up library created from many support classes and methods
for comfortable scripting on server and client side.
    - HTTP manipulation
    - URL operations
"""

__modulename__ = "httptools"
__author__ = "Stanislav Heller, Pavel Novotny"
__email__ = "xhelle03@stud.fit.vutbr.cz, xnovot28@stud.fit.vutbr.cz"
__date__ = "$31-May-2010 10:21:47$"


import httplib
import re
import os
import socket
from urlparse import urlparse, urlunsplit, urlsplit
import urllib
import time


def is_url_alive(url, timeout=10):
    """
    Send simple HEAD request and check if URL is active (ok, redirected, found).
    """
    def_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    for i in range(10):
        try:
            p = urlparse(url)
            h = httplib.HTTP(p[1])
            try:
                h.putrequest('HEAD', p[2])
                h.endheaders()
            except:
                socket.setdefaulttimeout(def_timeout)
                return False
            if h.getreply()[0] in (httplib.OK, httplib.MOVED_PERMANENTLY, \
                                   httplib.FOUND, httplib.SEE_OTHER, \
                                   httplib.TEMPORARY_REDIRECT):
                socket.setdefaulttimeout(def_timeout)
                return True
            else:
                socket.setdefaulttimeout(def_timeout)
                return False
        except socket.timeout:
            socket.setdefaulttimeout(def_timeout)
            return False
        except socket.error:
            time.sleep(0.3)
            continue
        except:
            return False
    else:
        return False


def is_url_valid(url):
    """
    Check if URL is valid using RE.
    """
    if not re.search('^(http|https|ftp)' + # scheme
                     '\://[a-z0-9\-\.]+\.[a-z]{2,3}(:[a-z0-9]*)?/?' + # path
                     '([\:a-z0-9\-\._\?\,\'/\\\+&amp;%\$#\=~])*' + # query, fragment
                     '$', url, re.I):
        return False
    return True


def get_file_name(url):
    """
    Get file name returns name of file parsed from url.
    Dots are translated to underscores, suffix is omitted.
    """
    spliturl = urlsplit(url)
    filename = os.path.basename(spliturl.path) # split('/')[-1]
    if not filename or re.search("\?", url):
        # link is with GET parameters, ask server for file name
        spliturl = urlsplit(url)
        try:
            conn = httplib.HTTPConnection(spliturl.netloc)
            conn.request("HEAD", "/" + spliturl.path + "?" + spliturl.query)
            resp = conn.getresponse()
            headers = resp.getheaders()
        except:
            return filename
        for head in headers:
            if head[0] == 'content-disposition':
                fn = re.search("(?<=filename\=)[^/]+", head[1])
                if not fn: return filename
                fname = fn.group(0)
                commas = re.search("\"[^\"]+\"", fname)
                if not commas: return fname
                return fname.replace('\"', '')
    return filename


def url_safe(s, charset='utf-8'):
    """Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.  This
    function can fix some of the problems in a similar way browsers
    handle data entered by the user:
    """
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlunsplit((scheme, netloc, path, qs, anchor))
